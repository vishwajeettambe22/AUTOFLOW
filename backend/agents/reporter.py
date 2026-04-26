import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core.llm import call_llm_tracked, _is_quota_error
from core import events

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Reporter agent in AutoFlow.

Your job: Take raw research content and polish it into a professional, well-structured markdown report.
You must preserve ALL information — never shorten, summarize, or omit content.
Your output must be at least as long as the input.
"""


async def reporter_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]

    await events.emit_agent_start(run_id, "reporter")
    log.info("reporter_start", run_id=run_id)

    # Calculate total cost
    total_cost = sum(u.get("cost_usd", 0) for u in state.get("token_usage", []))

    research_content = state.get('research_output', 'N/A')

    user_prompt = f"""
Polish and format the following research content into a clean, professional markdown report.

RESEARCH CONTENT:
{research_content[:4000]}

FORMATTING RULES:
- Keep ALL original information — do not remove, shorten, or summarize anything.
- Fix any formatting issues (broken tables, inconsistent headers, etc.)
- Ensure proper markdown syntax (headers, bold, lists, tables)
- The output MUST be at least as long as the input content above.
- Do NOT add new information that wasn't in the original.
- Do NOT add meta-commentary like "here is the report" or "this document covers".
- Start directly with the content (## Overview or similar).
"""

    try:
        response, usage, success = await call_llm_tracked(
            agent_name="reporter",
            model=settings.REPORTER_MODEL,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not success or not response.strip():
            raise ValueError("LLM call failed or returned empty response")

        # Detect quota errors in the response content
        if _is_quota_error(response):
            raise ValueError(f"Quota error in response: {response[:100]}")

        total_cost += usage.get("cost_usd", 0)

        await events.emit_agent_output(run_id, "reporter", response[:300] + "...")
        await events.emit_agent_done(run_id, "reporter", "success")
        await events.emit_token_usage(run_id, dict(usage))
        await events.emit_final(run_id, response, total_cost)

        return {
            "final_report": response,
            "total_cost_usd": total_cost,
            "reporter_status": AgentStatus.SUCCESS,
            "token_usage": [usage],
        }

    except Exception as e:
        log.error("reporter_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "reporter", "failed")
        return {
            "final_report": "",  # Empty report — not the error message
            "total_cost_usd": total_cost,
            "last_error": f"Reporter failed: {str(e)}",
            "reporter_status": AgentStatus.FAILED,
        }
