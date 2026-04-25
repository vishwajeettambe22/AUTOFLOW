import json
import uuid
import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus, SubTask
from core.llm import call_llm_tracked
from core import events

log = structlog.get_logger()

SYSTEM_PROMPT = """You are the Planner agent in an AI orchestration system called AutoFlow.

Your job: Given a user task, break it into 3-5 clear subtasks that other agents will execute.
The agents available are: researcher, coder, reviewer.

Output ONLY valid JSON in this exact format:
{
  "task_complexity": "simple" | "complex",
  "plan_summary": "One sentence describing the overall approach",
  "subtasks": [
    {"id": "t1", "description": "...", "assigned_to": "researcher"},
    {"id": "t2", "description": "...", "assigned_to": "coder"},
    {"id": "t3", "description": "...", "assigned_to": "reviewer"}
  ]
}

Rules:
- Keep subtasks focused and concrete
- researcher: gather information, look up facts, find examples
- coder: write code, generate structured documents, create tables
- reviewer: verify correctness, check completeness
- No more than 5 subtasks total
- Set task_complexity to "simple" for straightforward tasks, or "complex" if they require multiple iterations or deep review.
"""


async def planner_agent(state: AutoFlowState) -> dict:
    run_id = state["run_id"]
    user_task = state["user_task"]

    await events.emit_agent_start(run_id, "planner")
    log.info("planner_start", run_id=run_id, task=user_task[:80])

    user_prompt = f"User task: {user_task}"

    # If this is a re-plan after Critic, include context
    if state.get("critic_findings"):
        latest = state["critic_findings"][-1]
        user_prompt += f"""

IMPORTANT — This is a re-plan. The previous attempt failed.
Failed agent: {latest['failed_agent']}
Failure reason: {latest['failure_reason']}
Suggested fix: {latest['suggested_fix']}

Adjust the plan to address this failure.
"""

    try:
        response, usage, success = await call_llm_tracked(
            agent_name="planner",
            model=settings.PLANNER_MODEL,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        if not success or not response.strip():
            raise ValueError("LLM call failed or returned empty response")

        # Parse JSON response
        raw = response.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw.strip())

        subtasks: list[SubTask] = []
        for t in parsed.get("subtasks", []):
            subtasks.append(SubTask(
                id=t.get("id", str(uuid.uuid4())[:8]),
                description=t["description"],
                assigned_to=t["assigned_to"],
                status=AgentStatus.PENDING,
                output=None,
            ))

        await events.emit_agent_output(run_id, "planner", parsed["plan_summary"])
        await events.emit_agent_done(run_id, "planner", "success")
        await events.emit_token_usage(run_id, dict(usage))

        return {
            "subtasks": subtasks,
            "plan_summary": parsed.get("plan_summary", ""),
            "task_complexity": parsed.get("task_complexity", "complex").lower(),
            "planner_status": AgentStatus.SUCCESS,
            "token_usage": [usage],
        }

    except Exception as e:
        log.error("planner_failed", run_id=run_id, error=str(e))
        await events.emit_agent_done(run_id, "planner", "failed")
        return {
            "last_error": f"Planner failed: {str(e)}",
            "planner_status": AgentStatus.FAILED,
        }
