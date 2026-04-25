import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core.llm import call_llm_tracked
from core import events

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Reporter agent in AutoFlow.

Your job: Synthesize all agent outputs into a final, polished, well-structured response.

Guidelines:
- Write in clean markdown
- Start with an executive summary (2-3 sentences)
- Include all key information from research and coder output
- Organize with clear headers and sections
- End with a "Key Takeaways" section
- Make it immediately useful — the user should not need to read anything else
- Preserve any code blocks, tables, or structured content from the coder
"""


async def reporter_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]

    await events.emit_agent_start(run_id, "reporter")
    log.info("reporter_start", run_id=run_id)

    # Calculate total cost
    total_cost = sum(u.get("cost_usd", 0) for u in state.get("token_usage", []))

    user_prompt = f"""Original task: {state['user_task']}

Plan: {state.get('plan_summary', '')}

Research findings:
{state.get('research_output', 'N/A')[:3000]}

Generated content/code:
{state.get('code_output', 'N/A')[:3000]}

Review summary:
{state.get('review_output', 'N/A')[:500]}

Please synthesize this into a comprehensive final response.
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
            "final_report": state.get("code_output", ""),  # Fallback to coder output
            "total_cost_usd": total_cost,
            "last_error": f"Reporter failed: {str(e)}",
            "reporter_status": AgentStatus.FAILED,
        }
