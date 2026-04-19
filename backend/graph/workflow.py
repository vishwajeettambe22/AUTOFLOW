from langgraph.graph import StateGraph, END
import structlog

from core.state import AutoFlowState
from core.config import settings
from agents.planner import planner_agent
from agents.researcher import researcher_agent
from agents.coder import coder_agent
from agents.reviewer import reviewer_agent
from agents.critic import critic_agent
from agents.reporter import reporter_agent

log = structlog.get_logger()


# ─── Conditional edge functions ───────────────────────────────────────────────

def after_researcher(state: AutoFlowState) -> str:
    """Route after researcher: to coder, or to critic if research failed."""
    if not state.get("research_output"):
        retries = state.get("researcher_retry_count", 0)
        if retries >= settings.MAX_RESEARCHER_RETRIES:
            log.warning("researcher_max_retries", retries=retries)
            return "coder"  # Proceed with empty research rather than loop forever
        return "critic"
    return "coder"


def after_reviewer(state: AutoFlowState) -> str:
    """Route after reviewer: to reporter if passed, or to critic if failed."""
    if state.get("review_passed"):
        return "reporter"
    coder_retries = state.get("coder_retry_count", 0)
    total = state.get("total_iterations", 0)
    if coder_retries >= settings.MAX_CODER_RETRIES or total >= settings.MAX_TOTAL_ITERATIONS:
        log.warning("max_retries_hit", coder_retries=coder_retries, total=total)
        return "reporter"  # Report best effort
    return "critic"


def after_critic(state: AutoFlowState) -> str:
    """Route after critic: back to the appropriate agent for retry."""
    # Critic sets current_agent in its return value
    target = state.get("current_agent", "coder")
    valid_targets = {"planner", "researcher", "coder"}
    if target not in valid_targets:
        return "coder"
    return target


# ─── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AutoFlowState)

    # Register all agent nodes
    graph.add_node("planner", planner_agent)
    graph.add_node("researcher", researcher_agent)
    graph.add_node("coder", coder_agent)
    graph.add_node("reviewer", reviewer_agent)
    graph.add_node("critic", critic_agent)
    graph.add_node("reporter", reporter_agent)

    # Entry point
    graph.set_entry_point("planner")

    # Fixed edges
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "coder")  # Default — overridden by conditional below

    # Actually use conditional after researcher
    graph.add_conditional_edges(
        "researcher",
        after_researcher,
        {
            "coder": "coder",
            "critic": "critic",
        }
    )

    # Coder always goes to reviewer
    graph.add_edge("coder", "reviewer")

    # Reviewer routes based on review result
    graph.add_conditional_edges(
        "reviewer",
        after_reviewer,
        {
            "reporter": "reporter",
            "critic": "critic",
        }
    )

    # Critic routes back to the appropriate agent
    graph.add_conditional_edges(
        "critic",
        after_critic,
        {
            "planner": "planner",
            "researcher": "researcher",
            "coder": "coder",
        }
    )

    # Reporter is the terminal node
    graph.add_edge("reporter", END)

    return graph.compile()


# Compile once at module load
workflow = build_graph()
