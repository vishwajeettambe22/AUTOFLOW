from langgraph.graph import StateGraph, END
import structlog

from core.state import AutoFlowState, AgentStatus
from core.config import settings
from agents.planner import planner_agent
from agents.researcher import researcher_agent
from agents.coder import coder_agent
from agents.reviewer import reviewer_agent
from agents.critic import critic_agent
from agents.reporter import reporter_agent

log = structlog.get_logger()


# ─── Conditional edge functions ───────────────────────────────────────────────

def after_planner(state: AutoFlowState) -> str:
    """Route after planner: to researcher, or END if planner failed."""
    if state.get("planner_status") == AgentStatus.FAILED:
        log.warning("early_termination_planner_failed")
        return END
    return "researcher"


def after_researcher(state: AutoFlowState) -> str:
    """Route after researcher: to coder, or to critic if research failed."""
    if state.get("researcher_status") == AgentStatus.FAILED or not state.get("research_output"):
        retries = state.get("researcher_retry_count", 0)
        critic_iters = len(state.get("critic_findings", []))
        if retries >= settings.MAX_RESEARCHER_RETRIES or state.get("task_complexity") == "simple" or critic_iters >= settings.MAX_CRITIC_ITERATIONS:
            log.warning("early_termination_researcher_failed", retries=retries)
            return END
        return "critic"
    return "coder"


def after_coder(state: AutoFlowState) -> str:
    """Route after coder: to reviewer, or to critic/END if failed."""
    if state.get("coder_status") == AgentStatus.FAILED or not state.get("code_output"):
        retries = state.get("coder_retry_count", 0)
        total = state.get("total_iterations", 0)
        critic_iters = len(state.get("critic_findings", []))
        if retries >= settings.MAX_CODER_RETRIES or total >= settings.MAX_TOTAL_ITERATIONS or state.get("task_complexity") == "simple" or critic_iters >= settings.MAX_CRITIC_ITERATIONS:
            log.warning("early_termination_coder_failed", retries=retries)
            return END
        return "critic"
        
    if state.get("task_complexity") == "simple":
        return "reporter"
    return "reviewer"


def after_reviewer(state: AutoFlowState) -> str:
    """Route after reviewer: to reporter if passed, or to critic if failed."""
    if state.get("review_passed"):
        return "reporter"
    coder_retries = state.get("coder_retry_count", 0)
    total = state.get("total_iterations", 0)
    critic_iters = len(state.get("critic_findings", []))
    if coder_retries >= settings.MAX_CODER_RETRIES or total >= settings.MAX_TOTAL_ITERATIONS or state.get("task_complexity") == "simple" or critic_iters >= settings.MAX_CRITIC_ITERATIONS:
        log.warning("early_termination_reviewer_failed", coder_retries=coder_retries, total=total)
        return END
    return "critic"


def after_critic(state: AutoFlowState) -> str:
    """Route after critic: back to the appropriate agent for retry."""
    if state.get("critic_status") == AgentStatus.FAILED:
        return END
    # Critic sets next_retry_agent in its return value
    target = state.get("next_retry_agent", "coder")
    valid_targets = {"planner", "researcher", "coder"}
    if target not in valid_targets:
        return END
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

    # Planner conditionally routes to researcher
    graph.add_conditional_edges(
        "planner",
        after_planner,
        {
            "researcher": "researcher",
            END: END,
        }
    )

    # Use conditional after researcher
    graph.add_conditional_edges(
        "researcher",
        after_researcher,
        {
            "coder": "coder",
            "critic": "critic",
            END: END,
        }
    )

    # Use conditional after coder
    graph.add_conditional_edges(
        "coder",
        after_coder,
        {
            "reviewer": "reviewer",
            "reporter": "reporter",
            "critic": "critic",
            END: END,
        }
    )

    # Reviewer routes based on review result
    graph.add_conditional_edges(
        "reviewer",
        after_reviewer,
        {
            "reporter": "reporter",
            "critic": "critic",
            END: END,
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
            END: END,
        }
    )

    # Reporter is the terminal node
    graph.add_edge("reporter", END)

    return graph.compile()


# Compile once at module load
workflow = build_graph()
