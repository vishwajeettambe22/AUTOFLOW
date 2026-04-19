from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AutoFlow"
    DEBUG: bool = False
    API_VERSION: str = "v1"

    # LLM
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "anthropic"  # "anthropic" | "openai"
    DEFAULT_MODEL: str = "claude-3-5-sonnet-20241022"
    PLANNER_MODEL: str = "claude-3-5-sonnet-20241022"
    RESEARCHER_MODEL: str = "claude-3-5-sonnet-20241022"
    CODER_MODEL: str = "claude-3-5-sonnet-20241022"
    REVIEWER_MODEL: str = "claude-3-haiku-20240307"
    REPORTER_MODEL: str = "claude-3-haiku-20240307"
    CRITIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL: int = 3600  # 1 hour

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://autoflow:autoflow@127.0.0.1:5433/autoflow"
    # Code execution sandbox
    CODE_EXEC_TIMEOUT: int = 15  # seconds
    CODE_EXEC_MAX_OUTPUT: int = 4096  # chars

    # Agent limits
    MAX_RESEARCHER_RETRIES: int = 2
    MAX_CODER_RETRIES: int = 2
    MAX_TOTAL_ITERATIONS: int = 10

    # Cost per 1M tokens (USD) — update as needed
    COST_MAP: dict = {
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    }

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
