import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core.llm import call_llm_tracked
from core import events
from tools.search import web_search

log = structlog.get_logger()

async def researcher_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]
    user_task = state["user_task"]

    await events.emit_agent_start(run_id, "researcher")
    log.info("researcher_start", run_id=run_id)

    # Perform web search directly with user task
    await events.emit(run_id, "agent_log", {"agent": "researcher", "message": f"Searching: {user_task[:120]}"})
    search_results = await web_search(user_task[:120])

    if not search_results or "No search results" in search_results or "Search failed" in search_results:
        log.warning("researcher_fallback_to_knowledge", run_id=run_id)
        search_results = "No recent web data available. Please rely on your internal knowledge."

    user_prompt = f"""
TASK: {user_task}

REFERENCE DATA (use this as your primary source):
{search_results}

INSTRUCTIONS:
You must produce a COMPREHENSIVE research report. Follow the structure below EXACTLY.

## Overview
Write a 2-3 sentence introduction explaining the topic and why it matters.

## Top 3 Items

### 1. [Name]
**What it is:** One-sentence description.
**Key Strengths:**
- Strength 1: Explain in 1-2 sentences with specific details
- Strength 2: Explain in 1-2 sentences with specific details
- Strength 3: Explain in 1-2 sentences with specific details
**Best For:** Who should use this and when.

### 2. [Name]
(Same structure as above)

### 3. [Name]
(Same structure as above)

## Comparison Table
| Feature | Item 1 | Item 2 | Item 3 |
|---------|--------|--------|--------|
| (at least 5 rows comparing specific attributes) |

## Conclusion
Write a 3-4 sentence summary with a clear recommendation for different use cases.

CRITICAL RULES:
- Your response MUST be at least 500 words. Short responses are UNACCEPTABLE.
- Every section must have substantial content — no one-liners.
- Use real, specific, factual information from the reference data above.
- Do NOT use filler phrases like "in conclusion" or "as mentioned above".
- Do NOT include meta-commentary about yourself or the report.
- Go straight into the content starting with ## Overview.
"""

    try:
        response, usage, success = await call_llm_tracked(
            agent_name="researcher",
            model=settings.RESEARCHER_MODEL,
            system_prompt="You are a senior research analyst.",
            user_prompt=user_prompt,
        )

        if not success or not response.strip():
            raise ValueError("LLM call failed or returned empty response")

        if "Quota reached" in response:
            await events.emit_agent_done(run_id, "researcher", "failed")
            return {
                "research_output": response,
                "researcher_status": AgentStatus.FAILED,
                "last_error": response,
            }

        await events.emit_agent_output(run_id, "researcher", response[:500] + "...")
        await events.emit_agent_done(run_id, "researcher", "success")
        if usage:
            await events.emit_token_usage(run_id, dict(usage))

        return {
            "research_output": response,
            "researcher_status": AgentStatus.SUCCESS,
            "token_usage": [usage] if usage else [],
        }

    except Exception as e:
        log.error("researcher_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "researcher", "failed")
        return {
            "research_output": "Error during research.",
            "last_error": f"Researcher LLM call failed: {str(e)}",
            "researcher_status": AgentStatus.FAILED,
        }
