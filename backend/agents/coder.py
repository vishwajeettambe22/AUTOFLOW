import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core.llm import call_llm_tracked
from core import events
from tools.code_exec import execute_code

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Coder agent in AutoFlow.

Your job: Based on research notes, produce the requested output — code, reports, tables, or structured documents.

Guidelines:
- If writing code, make it clean, well-commented, and runnable
- If writing a report/document, use clear markdown formatting with headers and sections
- If creating a comparison table, use proper markdown tables
- Use the research notes provided — do not make up facts
- If you write Python code that can be executed to validate your output, wrap it in <execute>...</execute> tags
- Output high-quality, complete content — not placeholders
"""


async def coder_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]
    subtasks = state.get("subtasks", [])

    await events.emit_agent_start(run_id, "coder")
    log.info("coder_start", run_id=run_id)

    coder_tasks = [t for t in subtasks if t["assigned_to"] == "coder"]
    if not coder_tasks:
        await events.emit_agent_done(run_id, "coder", "skipped")
        return {
            "code_output": "No coder tasks assigned.",
            "agent_statuses": {**state.get("agent_statuses", {}), "coder": AgentStatus.SKIPPED},
        }

    task_text = "\n".join(f"- {t['description']}" for t in coder_tasks)

    # Include Critic feedback if retrying
    retry_context = ""
    if state.get("coder_retry_count", 0) > 0 and state.get("critic_findings"):
        latest = state["critic_findings"][-1]
        retry_context = f"""
RETRY CONTEXT:
Previous attempt failed. Reviewer issue: {latest.get('failure_reason', 'Unknown')}
Suggested fix: {latest.get('suggested_fix', 'Try again with improvements')}
Previous output had issues — please produce an improved version.
"""

    user_prompt = f"""Original user task: {state['user_task']}

Coder subtasks to complete:
{task_text}

Research notes available:
{state.get('research_output', 'No research available')}

{retry_context}

Produce the requested output now.
"""

    try:
        response, usage = await call_llm_tracked(
            agent_name="coder",
            model=settings.CODER_MODEL,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Check for executable code blocks and run them
        exec_result = None
        if "<execute>" in response:
            code_start = response.index("<execute>") + 9
            code_end = response.index("</execute>")
            code_to_run = response[code_start:code_end].strip()
            await events.emit(run_id, "agent_log", {"agent": "coder", "message": "Executing code..."})
            exec_result = await execute_code(code_to_run)
            if exec_result["success"]:
                response += f"\n\n**Execution output:**\n```\n{exec_result['stdout']}\n```"
            else:
                response += f"\n\n**Execution failed:**\n```\n{exec_result['stderr']}\n```"

        await events.emit_agent_output(run_id, "coder", response[:500] + "...")
        await events.emit_agent_done(run_id, "coder", "success")
        await events.emit_token_usage(run_id, dict(usage))

        updated = []
        for t in subtasks:
            if t["assigned_to"] == "coder":
                updated.append({**t, "status": AgentStatus.SUCCESS, "output": response[:200]})
            else:
                updated.append(t)

        return {
            "code_output": response,
            "subtasks": updated,
            "current_agent": "reviewer",
            "agent_statuses": {**state.get("agent_statuses", {}), "coder": AgentStatus.SUCCESS},
            "token_usage": [usage],
        }

    except Exception as e:
        log.error("coder_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "coder", "failed")
        return {
            "code_output": "",
            "last_error": f"Coder failed: {str(e)}",
            "agent_statuses": {**state.get("agent_statuses", {}), "coder": AgentStatus.FAILED},
        }
