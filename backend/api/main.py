import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core import events
from graph.workflow import workflow
from memory.redis_store import set_run_status, get_run_status, set_run_state
from memory.postgres_store import init_db, save_run, get_run_by_id, get_all_runs
from core.llm import _is_quota_error

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("autoflow_started")
    yield
    log.info("autoflow_stopped")


app = FastAPI(
    title="AutoFlow API",
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response models ─────────────────────────────────────────────────

class RunTaskRequest(BaseModel):
    task: str
    run_id: str | None = None  # Allow client to provide run_id for WS correlation


class RunTaskResponse(BaseModel):
    run_id: str
    status: str
    final_report: str
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    error: Optional[str] = None


class RunResultResponse(BaseModel):
    run_id: str
    task: str
    status: str
    final_report: str
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


# ─── Core task runner ──────────────────────────────────────────────────────────

async def execute_workflow(run_id: str, user_task: str):
    """Run the full LangGraph workflow for a task."""
    await set_run_status(run_id, "running")

    initial_state = AutoFlowState(
        run_id=run_id,
        user_task=user_task,
        subtasks=[],
        plan_summary="",
        research_output="",
        code_output="",
        review_output="",
        review_passed=False,
        final_report="",
        critic_findings=[],
        researcher_retry_count=0,
        coder_retry_count=0,
        total_iterations=0,
        next_retry_agent=None,
        planner_status=AgentStatus.PENDING,
        researcher_status=AgentStatus.PENDING,
        coder_status=AgentStatus.PENDING,
        reviewer_status=AgentStatus.PENDING,
        critic_status=AgentStatus.PENDING,
        reporter_status=AgentStatus.PENDING,
        token_usage=[],
        total_cost_usd=0.0,
        last_error=None,
    )

    try:
        final_state = await workflow.ainvoke(initial_state)  
        
        final_report = final_state.get("final_report", "")
        has_error = final_state.get("last_error")
        is_quota = _is_quota_error(final_report) if final_report else False
        
        if not final_report.strip() or has_error or is_quota:
            await set_run_status(run_id, "failed")
            log.warning("run_marked_failed", run_id=run_id, 
                       has_report=bool(final_report.strip()), 
                       has_error=bool(has_error), is_quota=is_quota)
        else:
            await set_run_status(run_id, "success")
            
        await set_run_state(run_id, {k: v for k, v in final_state.items() if k != "token_usage"})
        await save_run(final_state)
        return final_state

    except Exception as e:
        log.error("workflow_failed", run_id=run_id, error=str(e))
        await set_run_status(run_id, "failed")
        await events.emit_error(run_id, "system", str(e))
        raise


# ─── REST Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/v1/run-task", response_model=RunTaskResponse)
async def run_task(req: RunTaskRequest):
    """
    Run an AutoFlow task and return the full report.
    This endpoint waits for the workflow to complete before responding.
    """
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    run_id = req.run_id or str(uuid.uuid4())

    try:
        final_state = await execute_workflow(run_id, req.task.strip())

        token_usage = final_state.get("token_usage", [])
        total_input = sum(u.get("input_tokens", 0) for u in token_usage)
        total_output = sum(u.get("output_tokens", 0) for u in token_usage)

        final_report = final_state.get("final_report", "")
        last_error = final_state.get("last_error")
        status = "success" if final_report.strip() and not last_error else "failed"

        return RunTaskResponse(
            run_id=run_id,
            status=status,
            final_report=final_report,
            total_cost_usd=round(final_state.get("total_cost_usd", 0), 6),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            error=last_error,
        )
    except Exception as e:
        log.error("run_task_error", run_id=run_id, error=str(e))
        return RunTaskResponse(
            run_id=run_id,
            status="failed",
            final_report="",
            total_cost_usd=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            error=str(e),
        )


@app.get("/api/v1/run/{run_id}/result", response_model=RunResultResponse)
async def get_result(run_id: str):
    """Retrieve the full result of a completed run from the database."""
    run = await get_run_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResultResponse(
        run_id=run.id,
        task=run.user_task,
        status=run.status,
        final_report=run.final_report or "",
        total_cost_usd=round(run.total_cost_usd or 0, 6),
        total_input_tokens=run.total_input_tokens or 0,
        total_output_tokens=run.total_output_tokens or 0,
        created_at=str(run.created_at) if run.created_at else None,
        completed_at=str(run.completed_at) if run.completed_at else None,
    )


@app.get("/api/v1/run/{run_id}/status")
async def get_status(run_id: str):
    status = await get_run_status(run_id)
    if not status:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "status": status}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.API_VERSION}


# ─── WebSocket endpoint ────────────────────────────────────────────────────────

@app.get("/api/v1/runs")
async def list_runs():
    """Return all past runs, most recent first."""
    runs = await get_all_runs()
    return {
        "runs": [
            {
                "run_id": r.id,
                "user_task": r.user_task,
                "status": r.status,
                "final_report": r.final_report or "",
                "total_cost_usd": round(r.total_cost_usd or 0, 6),
                "total_input_tokens": r.total_input_tokens or 0,
                "total_output_tokens": r.total_output_tokens or 0,
                "created_at": str(r.created_at) if r.created_at else None,
                "completed_at": str(r.completed_at) if r.completed_at else None,
            }
            for r in runs
        ]
    }


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await websocket.accept()
    events.register(run_id, websocket)
    log.info("ws_connected", run_id=run_id)

    try:
        # Keep connection alive until client disconnects
        while True:
            data = await websocket.receive_text()
            # Echo heartbeat
            if data == "ping":
                await websocket.send_text('{"event":"pong","data":{}}')
    except WebSocketDisconnect:
        log.info("ws_disconnected", run_id=run_id)
    finally:
        events.unregister(run_id)
