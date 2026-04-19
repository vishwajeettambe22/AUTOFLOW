import json
import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus, CriticFinding
from core.llm import call_llm_tracked
from core import events

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Critic agent in AutoFlow — the self-healing brain.

Your job: When another agent fails, analyze WHY and prescribe an intelligent fix.

You receive:
- Which agent failed
- The error/issue
- The current plan and outputs

Diagnose the root cause and suggest a specific fix. Do NOT suggest the same approach again.

Output ONLY valid JSON:
{
  "failed_agent": "researcher|coder|reviewer",
  "failure_reason": "specific reason why it failed",
  "root_cause": "underlying issue (bad prompt, missing data, wrong approach, etc.)",
  "suggested_fix": "specific actionable change for the retry",
  "retry_target": "researcher|coder|planner",
  "modified_instruction": "rewritten instruction/prompt for the retry"
}

Be specific. Vague fixes like 'try again' are not acceptable.
"""


async def critic_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]
    total_iterations = state.get("total_iterations", 0) + 1
    researcher_retries = state.get("researcher_retry_count", 0)
    coder_retries = state.get("coder_retry_count", 0)

    await events.emit_agent_start(run_id, "critic")
    log.info("critic_start", run_id=run_id, iterations=total_iterations)

    # Determine what failed
    last_error = state.get("last_error", "Unknown error")
    review_output = state.get("review_output", "")

    # Build context for Critic
    failed_agent = "coder"
    if not state.get("research_output"):
        failed_agent = "researcher"
    elif not state.get("review_passed", True) and state.get("code_output"):
        failed_agent = "coder"

    user_prompt = f"""Original task: {state['user_task']}

Plan summary: {state.get('plan_summary', '')}

Failed agent: {failed_agent}
Error/Issue: {last_error}

Review output (if available):
{review_output[:1000] if review_output else 'N/A'}

Research output (if available):
{state.get('research_output', 'N/A')[:500]}

Coder output (if available):
{state.get('code_output', 'N/A')[:500]}

Previous critic findings: {len(state.get('critic_findings', []))} previous attempts.

Analyze the failure and prescribe a fix.
"""

    try:
        response, usage = await call_llm_tracked(
            agent_name="critic",
            model=settings.CRITIC_MODEL,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())

        finding = CriticFinding(
            failed_agent=parsed.get("failed_agent", failed_agent),
            failure_reason=parsed.get("failure_reason", last_error),
            suggested_fix=parsed.get("suggested_fix", ""),
            retry_count=total_iterations,
        )

        retry_target = parsed.get("retry_target", "coder")

        await events.emit_agent_output(
            run_id, "critic",
            f"Root cause: {parsed.get('root_cause', '')} | Fix: {parsed.get('suggested_fix', '')}"
        )
        await events.emit_agent_done(run_id, "critic", "success")
        await events.emit_token_usage(run_id, dict(usage))

        result = {
            "critic_findings": [finding],
            "total_iterations": total_iterations,
            "current_agent": retry_target,
            "agent_statuses": {**state.get("agent_statuses", {}), "critic": AgentStatus.SUCCESS},
            "token_usage": [usage],
            "last_error": None,
        }

        # Increment the correct retry counter
        if retry_target == "researcher":
            result["researcher_retry_count"] = researcher_retries + 1
            result["research_output"] = ""  # Reset for retry
        elif retry_target == "coder":
            result["coder_retry_count"] = coder_retries + 1
            result["code_output"] = ""  # Reset for retry
        elif retry_target == "planner":
            result["subtasks"] = []
            result["plan_summary"] = ""

        return result

    except Exception as e:
        log.error("critic_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "critic", "failed")
        return {
            "total_iterations": total_iterations,
            "last_error": f"Critic failed: {str(e)}",
            "agent_statuses": {**state.get("agent_statuses", {}), "critic": AgentStatus.FAILED},
        }
