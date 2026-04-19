import time
from typing import Optional, Any
from pydantic import SecretStr
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import structlog

from .config import settings
from .state import AgentTokenUsage

log = structlog.get_logger()


def get_llm(model: Optional[str] = None, temperature: float = 0.1) -> Any:
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    model = model or settings.DEFAULT_MODEL

    anthropic_kwargs = {}
    if settings.ANTHROPIC_API_KEY:
        anthropic_kwargs["api_key"] = SecretStr(settings.ANTHROPIC_API_KEY)

    openai_kwargs = {}
    if settings.OPENAI_API_KEY:
        openai_kwargs["api_key"] = settings.OPENAI_API_KEY

    if provider == "anthropic":
        return ChatAnthropic(
            model_name=model,
            temperature=temperature,
            timeout=None,
            stop=None,
            **anthropic_kwargs,
        )
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        **openai_kwargs,
    )

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = settings.COST_MAP.get(model, {"input": 3.0, "output": 15.0})
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


async def call_llm_tracked(
    agent_name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> tuple[str, AgentTokenUsage]:
    """
    Call LLM and return (response_text, token_usage).
    Wraps every LLM call in the system for cost tracking.
    """
    llm = get_llm(model=model, temperature=temperature)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    start = time.time()
    response = await llm.ainvoke(messages)
    elapsed = time.time() - start

    # Extract token usage from response metadata
    usage_meta = response.usage_metadata or {}
    input_tokens = usage_meta.get("input_tokens", 0)
    output_tokens = usage_meta.get("output_tokens", 0)
    cost = calculate_cost(model, input_tokens, output_tokens)

    usage = AgentTokenUsage(
        agent=agent_name,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )

    log.info(
        "llm_call_complete",
        agent=agent_name,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=round(cost, 6),
        elapsed_s=round(elapsed, 2),
    )

    content = response.content
    if isinstance(content, (list, dict)):
        content = str(content)

    return content, usage