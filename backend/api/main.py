import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

from core.config import settings
from core.state import AutoFlowState, AgentStatus
from core import events
from graph.workflow import workflow
from memory.redis_store import set_run_status, get_run_status, set_run_state
from memory.postgres_store import init_db, save_run

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
    message: str


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
        
        if not final_state.get("final_report") or final_state.get("last_error"):
            await set_run_status(run_id, "failed")
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
    Kick off an AutoFlow task run.
    Connect to WS /ws/{run_id} BEFORE calling this endpoint to receive live updates.
    """
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="Task cannot be empty")

    run_id = req.run_id or str(uuid.uuid4())

    # Fire and forget — client receives updates via WebSocket
    asyncio.create_task(execute_workflow(run_id, req.task.strip()))

    return RunTaskResponse(
        run_id=run_id,
        status="started",
        message=f"Task started. Connect to /ws/{run_id} for live updates.",
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
