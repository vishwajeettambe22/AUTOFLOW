import json
import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core.llm import call_llm_tracked
from core import events

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Reviewer agent in AutoFlow.

Your job: Review the coder's output against the original task requirements and research notes.

Check for:
1. Completeness — does it address all requirements?
2. Accuracy — is it consistent with the research notes?
3. Quality — is it well-structured and usable?
4. Correctness — if code, does it look syntactically valid?

Output ONLY valid JSON:
{
  "passed": true or false,
  "score": 1-10,
  "issues": ["issue 1", "issue 2"],
  "suggestions": ["suggestion 1"],
  "summary": "One sentence review verdict"
}

Be strict but fair. Pass (true) only if the output is genuinely good (score >= 7).
"""


async def reviewer_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]

    await events.emit_agent_start(run_id, "reviewer")
    log.info("reviewer_start", run_id=run_id)

    user_prompt = f"""Original task: {state['user_task']}

Plan summary: {state.get('plan_summary', '')}

Research output:
{state.get('research_output', 'N/A')[:2000]}

Coder output to review:
{state.get('code_output', 'N/A')[:3000]}

Review the coder's output now.
"""

    try:
        response, usage, success = await call_llm_tracked(
            agent_name="reviewer",
            model=settings.REVIEWER_MODEL,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not success or not response.strip():
            raise ValueError("LLM call failed or returned empty response")

        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())

        passed = parsed.get("passed", False)
        score = parsed.get("score", 0)
        summary = parsed.get("summary", "")

        await events.emit_agent_output(run_id, "reviewer", f"Score: {score}/10 — {summary}")
        await events.emit_agent_done(run_id, "reviewer", "success" if passed else "failed")
        await events.emit_token_usage(run_id, dict(usage))

        result = {
            "review_output": json.dumps(parsed, indent=2),
            "review_passed": passed,
            "reviewer_status": AgentStatus.SUCCESS,
            "token_usage": [usage],
        }

        if not passed:
            result["last_error"] = f"Review failed (score {score}/10): {'; '.join(parsed.get('issues', []))}"

        return result

    except Exception as e:
        log.error("reviewer_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "reviewer", "failed")
        return {
            "review_output": "",
            "review_passed": False,
            "last_error": f"Reviewer failed: {str(e)}",
            "reviewer_status": AgentStatus.FAILED,
        }
