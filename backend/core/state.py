from typing import TypedDict, List, Optional, Annotated
from enum import Enum
import operator


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentTokenUsage(TypedDict):
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class SubTask(TypedDict):
    id: str
    description: str
    assigned_to: str  # researcher | coder | reviewer
    status: AgentStatus
    output: Optional[str]


class CriticFinding(TypedDict):
    failed_agent: str
    failure_reason: str
    suggested_fix: str
    retry_count: int


# The central state object shared across all LangGraph nodes
class AutoFlowState(TypedDict):
    # Input
    run_id: str
    user_task: str
    
    # Planner output
    subtasks: List[SubTask]
    plan_summary: str
    
    # Agent outputs
    research_output: str
    code_output: str
    review_output: str
    review_passed: bool
    final_report: str
    
    # Self-healing
    critic_findings: Annotated[List[CriticFinding], operator.add]
    researcher_retry_count: int
    coder_retry_count: int
    total_iterations: int
    
    # Status tracking (streamed to frontend)
    current_agent: str
    agent_statuses: dict  # agent_name -> AgentStatus
    
    # Cost tracking
    token_usage: Annotated[List[AgentTokenUsage], operator.add]
    total_cost_usd: float
    
    # Error context
    last_error: Optional[str]
