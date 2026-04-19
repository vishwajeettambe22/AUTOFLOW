from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import structlog

from core.config import settings

log = structlog.get_logger()


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    user_task = Column(Text, nullable=False)
    plan_summary = Column(Text)
    final_report = Column(Text)
    status = Column(String, default="pending")  # pending|running|success|failed

    # Cost tracking
    total_cost_usd = Column(Float, default=0.0)
    planner_cost = Column(Float, default=0.0)
    researcher_cost = Column(Float, default=0.0)
    coder_cost = Column(Float, default=0.0)
    reviewer_cost = Column(Float, default=0.0)
    critic_cost = Column(Float, default=0.0)
    reporter_cost = Column(Float, default=0.0)

    # Token counts
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)

    # Metadata
    total_iterations = Column(Integer, default=0)
    review_passed = Column(Boolean, default=False)
    critic_invocations = Column(Integer, default=0)
    token_usage_breakdown = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


# Database engine (lazy initialized)
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL
        _engine = create_async_engine(db_url, echo=True)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db():
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("db_initialized")


async def save_run(state: dict):
    """Persist a completed run to PostgreSQL."""
    factory = get_session_factory()
    token_usage = state.get("token_usage", [])

    # Aggregate costs by agent
    agent_costs = {}
    for u in token_usage:
        agent = u.get("agent", "unknown")
        agent_costs[agent] = agent_costs.get(agent, 0) + u.get("cost_usd", 0)

    run = Run(
        id=state["run_id"],
        user_task=state["user_task"],
        plan_summary=state.get("plan_summary", ""),
        final_report=state.get("final_report", ""),
        status="success" if state.get("final_report") else "failed",
        total_cost_usd=state.get("total_cost_usd", 0),
        planner_cost=agent_costs.get("planner", 0),
        researcher_cost=agent_costs.get("researcher", 0),
        coder_cost=agent_costs.get("coder", 0),
        reviewer_cost=agent_costs.get("reviewer", 0),
        critic_cost=agent_costs.get("critic", 0),
        reporter_cost=agent_costs.get("reporter", 0),
        total_input_tokens=sum(u.get("input_tokens", 0) for u in token_usage),
        total_output_tokens=sum(u.get("output_tokens", 0) for u in token_usage),
        total_iterations=state.get("total_iterations", 0),
        review_passed=state.get("review_passed", False),
        critic_invocations=len(state.get("critic_findings", [])),
        token_usage_breakdown=token_usage,
        completed_at=datetime.utcnow(),
    )

    async with factory() as session:
        session.add(run)
        await session.commit()

    log.info("run_saved", run_id=state["run_id"], cost=round(state.get("total_cost_usd", 0), 4))
