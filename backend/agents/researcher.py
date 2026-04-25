import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core.llm import call_llm_tracked
from core import events
from tools.search import web_search

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Researcher agent in AutoFlow.

Your job: Research and gather relevant, accurate information to address the assigned subtasks.

You have access to web search results provided to you. Use them to extract key facts, examples, and data.

Guidelines:
- Be thorough but concise
- Cite sources when possible (URLs)
- If the search results are poor, say so explicitly — do not make up information
- Focus on the research subtasks, ignore coding or review tasks
- Output well-structured markdown
"""


async def researcher_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]
    subtasks = state.get("subtasks", [])

    await events.emit_agent_start(run_id, "researcher")
    log.info("researcher_start", run_id=run_id)

    # Extract research subtasks
    research_tasks = [t for t in subtasks if t["assigned_to"] == "researcher"]
    if not research_tasks:
        await events.emit_agent_done(run_id, "researcher", "skipped")
        return {
            "research_output": "No research tasks assigned.",
            "researcher_status": AgentStatus.SKIPPED,
        }

    # Build search query from task descriptions
    task_text = "\n".join(f"- {t['description']}" for t in research_tasks)
    search_query = state["user_task"][:120]  # Use the original task as query

    # Perform web search
    await events.emit(run_id, "agent_log", {"agent": "researcher", "message": f"Searching: {search_query}"})
    search_results = await web_search(search_query)

    if not search_results:
        log.warning("researcher_no_search_results", run_id=run_id)
        # Return a signal for Critic to handle
        return {
            "research_output": "",
            "last_error": "Web search returned no results",
            "researcher_retry_count": state.get("researcher_retry_count", 0),
            "researcher_status": AgentStatus.FAILED,
        }

    user_prompt = f"""Original user task: {state['user_task']}

Research subtasks to complete:
{task_text}

Web search results:
{search_results}

Please produce comprehensive research notes addressing the subtasks above.
"""

    try:
        response, usage, success = await call_llm_tracked(
            agent_name="researcher",
            model=settings.RESEARCHER_MODEL,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not success or not response.strip():
            raise ValueError("LLM call failed or returned empty response")

        await events.emit_agent_output(run_id, "researcher", response[:500] + "...")
        await events.emit_agent_done(run_id, "researcher", "success")
        await events.emit_token_usage(run_id, dict(usage))

        # Update subtask statuses
        updated = []
        for t in subtasks:
            if t["assigned_to"] == "researcher":
                updated.append({**t, "status": AgentStatus.SUCCESS, "output": response[:200]})
            else:
                updated.append(t)

        return {
            "research_output": response,
            "subtasks": updated,
            "researcher_status": AgentStatus.SUCCESS,
            "token_usage": [usage],
        }

    except Exception as e:
        log.error("researcher_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "researcher", "failed")
        return {
            "research_output": "",
            "last_error": f"Researcher LLM call failed: {str(e)}",
            "researcher_status": AgentStatus.FAILED,
        }
