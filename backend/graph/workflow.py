from langgraph.graph import StateGraph, END
import structlog

from core.state import AutoFlowState, AgentStatus
from core.config import settings
from agents.researcher import researcher_agent
from agents.reporter import reporter_agent

log = structlog.get_logger()


# ─── Routing logic ─────────────────────────────────────────────────────────────

def should_continue_after_researcher(state: AutoFlowState) -> str:
    """Skip reporter if researcher failed (quota exhausted, error, etc.)."""
    researcher_status = state.get("researcher_status")
    last_error = state.get("last_error")

    if researcher_status == AgentStatus.FAILED or last_error:
        log.warning("skipping_reporter", reason="researcher_failed", 
                     researcher_status=str(researcher_status), last_error=last_error)
        return "end"
    
    return "reporter"


# ─── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AutoFlowState)

    # Register agent nodes
    graph.add_node("researcher", researcher_agent)
    graph.add_node("reporter", reporter_agent)

    # Entry point
    graph.set_entry_point("researcher")

    # Conditional: only run reporter if researcher succeeded
    graph.add_conditional_edges(
        "researcher",
        should_continue_after_researcher,
        {"reporter": "reporter", "end": END}
    )
    graph.add_edge("reporter", END)

    return graph.compile()


# Compile once at module load
workflow = build_graph()
