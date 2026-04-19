import json
import asyncio
from typing import Optional, Any
from fastapi import WebSocket
import structlog

log = structlog.get_logger()

# Global registry: run_id -> WebSocket connection
_connections: dict[str, WebSocket] = {}


def register(run_id: str, ws: WebSocket):
    _connections[run_id] = ws


def unregister(run_id: str):
    _connections.pop(run_id, None)


async def emit(run_id: str, event: str, data: Any):
    ws = _connections.get(run_id)
    if not ws:
        return
    try:
        payload = json.dumps({"event": event, "data": data})
        await ws.send_text(payload)
    except Exception as e:
        log.warning("ws_send_failed", run_id=run_id, error=str(e))


async def emit_agent_start(run_id: str, agent: str):
    await emit(run_id, "agent_start", {"agent": agent, "status": "running"})


async def emit_agent_output(run_id: str, agent: str, output: str):
    await emit(run_id, "agent_output", {"agent": agent, "output": output})


async def emit_agent_done(run_id: str, agent: str, status: str = "success"):
    await emit(run_id, "agent_done", {"agent": agent, "status": status})


async def emit_token_usage(run_id: str, usage: dict):
    await emit(run_id, "token_usage", usage)


async def emit_error(run_id: str, agent: str, error: str):
    await emit(run_id, "error", {"agent": agent, "error": error})


async def emit_final(run_id: str, report: str, total_cost: float):
    await emit(run_id, "final", {"report": report, "total_cost_usd": round(total_cost, 6)})
