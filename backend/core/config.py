from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AutoFlow"
    DEBUG: bool = False
    API_VERSION: str = "v1"

    # LLM
    # LLM KEYS
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

# PROVIDER
    DEFAULT_LLM_PROVIDER: str = "gemini"

# MODELS (OpenAI)
    DEFAULT_MODEL: str = "gemini-2.5-flash"

    PLANNER_MODEL: str = "gemini-2.5-flash"
    RESEARCHER_MODEL: str = "gemini-2.5-flash"
    CODER_MODEL: str = "gemini-2.5-flash"
    REVIEWER_MODEL: str = "gemini-2.5-flash"
    REPORTER_MODEL: str = "gemini-2.5-flash"
    CRITIC_MODEL: str = "gemini-2.5-flash"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL: int = 3600  # 1 hour

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://autoflow:autoflow@127.0.0.1:5433/autoflow"
    # Code execution sandbox
    CODE_EXEC_TIMEOUT: int = 15  # seconds
    CODE_EXEC_MAX_OUTPUT: int = 4096  # chars

    MAX_RESEARCHER_RETRIES: int = 1
    MAX_CODER_RETRIES: int = 1
    MAX_TOTAL_ITERATIONS: int = 3
    MAX_CRITIC_ITERATIONS: int = 1

    # Rate limits
    MAX_REQUESTS_PER_MIN: int = 5
    MIN_DELAY: int = 12

    # Cost per 1M tokens (USD) — update as needed
    COST_MAP: dict = {
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.3},
        "gemini-1.5-pro": {"input": 3.5, "output": 10.5},
        "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
        "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
    }

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
