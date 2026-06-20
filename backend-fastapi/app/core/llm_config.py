"""Provider presets and resolution for the LLM service layer.

One protocol (OpenAI-compatible chat completions), N providers. The service
layer (app/services/langchain_glm_service.py) calls resolve_llm_config() and
never hardcodes a provider URL or model name.
"""
from dataclasses import dataclass
from typing import Optional

PROVIDER_PRESETS = {
    "zhipuai": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "models": {
            "default": "glm-5.2",
            "fast": "glm-4.7",
            "quality": "glm-5.2",
            "light": "glm-5.1",
        },
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": {
            "default": "gpt-4o",
            "fast": "gpt-4o-mini",
            "quality": "gpt-4o",
            "light": "gpt-4o-mini",
        },
    },
}

TIERS = ("default", "fast", "quality", "light")

_TIER_ENV_FIELD = {
    "default": "LLM_MODEL",
    "fast": "LLM_MODEL_FAST",
    "quality": "LLM_MODEL_QUALITY",
    "light": "LLM_MODEL_LIGHT",
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str  # may be "" — validated at first LLM use, not at resolution


def resolve_llm_config(
    settings,
    tier: str = "default",
    *,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMConfig:
    """Precedence per field: explicit argument > env override > provider preset.

    API key precedence: explicit > LLM_API_KEY > ZHIPUAI_API_KEY (backward
    compat with existing .env files).
    """
    raw_provider = settings.LLM_PROVIDER or "zhipuai"
    provider = raw_provider.lower()
    if provider not in PROVIDER_PRESETS:
        raise ValueError(
            f"Unknown LLM_PROVIDER {raw_provider!r}; expected one of {sorted(PROVIDER_PRESETS)}"
        )
    if tier not in TIERS:
        raise ValueError(f"Unknown tier {tier!r}; expected one of {TIERS}")

    preset = PROVIDER_PRESETS[provider]
    return LLMConfig(
        provider=provider,
        base_url=base_url or settings.LLM_BASE_URL or preset["base_url"],
        model=model or getattr(settings, _TIER_ENV_FIELD[tier], "") or preset["models"][tier],
        api_key=api_key or settings.LLM_API_KEY or settings.ZHIPUAI_API_KEY or "",
    )
