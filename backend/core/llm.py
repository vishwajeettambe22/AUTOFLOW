import time
import asyncio
from typing import Optional, Any
from pydantic import SecretStr
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from google import genai
from langchain_core.messages import HumanMessage, SystemMessage
import structlog

from .config import settings
from .state import AgentTokenUsage

log = structlog.get_logger()

# Markers that indicate a quota/rate-limit error in the response content
QUOTA_ERROR_MARKERS = ["quota reached", "try again later", "resource exhausted", "rate limit"]


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


def _is_quota_error(text: str) -> bool:
    """Check if response text indicates a quota/rate-limit error."""
    lower = text.lower()
    return any(marker in lower for marker in QUOTA_ERROR_MARKERS)


async def call_gemini(system_prompt: str, user_prompt: str, model_name: str, temperature: float = 0.7) -> tuple[str, int, int, bool]:
    content = ""
    input_tokens = 0
    output_tokens = 0
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    
    for attempt in range(3):
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,  # Only user prompt as content
                config={
                    "system_instruction": system_prompt,  # System prompt goes here only
                    "temperature": temperature,
                    "max_output_tokens": 8192
                }
            )
            
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                
            log.info("gemini_raw_response", 
                      has_candidates=bool(response.candidates),
                      input_tokens=input_tokens, 
                      output_tokens=output_tokens)
            try:
                if response.candidates and response.candidates[0].content.parts:
                    content = "".join([
                        part.text for part in response.candidates[0].content.parts
                        if hasattr(part, "text")
                    ])
                else:
                    content = ""
                
                if not content:
                    content = str(response)
            except Exception:
                # Handle cases where response parsing throws an exception
                content = str(response)
                
            break  # Success or safety block, break out of loop
            
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "resource" in err_str:
                log.warning("gemini_quota_exhausted", attempt=attempt+1, error=str(e))
                content = "Quota reached. Try again later."
                break
            if attempt < 2:  # Retry on all 3 attempts, not just the first
                delay = (2 ** attempt) * 5
                log.warning("gemini_retry_backoff", attempt=attempt+1, delay=delay, error=str(e))
                await asyncio.sleep(delay)
                continue
            log.error("gemini_call_failed", error=str(e))
            break
    
    # Properly detect quota errors in the content
    success = bool(content.strip()) and not _is_quota_error(content)
    return content, input_tokens, output_tokens, success

async def call_llm_tracked(
    agent_name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> tuple[str, AgentTokenUsage, bool]:
    """
    Call LLM and return (response_text, token_usage).
    Wraps every LLM call in the system for cost tracking.
    """
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    start = time.time()
    
    # Global throttling before every call
    log.info("llm_throttle_delay", delay=settings.MIN_DELAY)
    await asyncio.sleep(settings.MIN_DELAY)
    
    content = ""
    input_tokens = 0
    output_tokens = 0

    success = False

    try:
        if provider == "gemini":
            content, input_tokens, output_tokens, gemini_success = await call_gemini(
                system_prompt, user_prompt, model, temperature
            )
            success = gemini_success
        else:
            llm = get_llm(model=model, temperature=temperature)
        
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        
            response = await llm.ainvoke(messages)
        
            # Extract token usage from response metadata
            usage_meta = getattr(response, "usage_metadata", None) or {}
            input_tokens = usage_meta.get("input_tokens", 0)
            output_tokens = usage_meta.get("output_tokens", 0)
            
            raw_content = response.content
            if isinstance(raw_content, (list, dict)):
                content = str(raw_content)
            else:
                content = str(raw_content) if raw_content is not None else ""
            
            success = bool(content.strip()) and not _is_quota_error(content)
                
    except Exception as e:
        log.error("llm_call_failed", agent=agent_name, provider=provider, error=str(e))
        success = False

    elapsed = time.time() - start
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
        success=success,
    )

    return content, usage, success