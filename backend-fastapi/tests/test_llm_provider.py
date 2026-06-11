"""Tests for provider preset resolution (app/core/llm_config.py)."""
from types import SimpleNamespace

import pytest

from app.core.llm_config import PROVIDER_PRESETS, TIERS, resolve_llm_config


def fake_settings(**overrides):
    """All LLM fields empty unless overridden. SimpleNamespace, not MagicMock,
    so unset attributes are real empty strings rather than truthy mocks."""
    base = dict(
        LLM_PROVIDER="zhipuai", LLM_API_KEY="", LLM_BASE_URL="",
        LLM_MODEL="", LLM_MODEL_FAST="", LLM_MODEL_QUALITY="", LLM_MODEL_LIGHT="",
        ZHIPUAI_API_KEY="",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestPresetResolution:
    def test_zhipuai_default_tier(self):
        cfg = resolve_llm_config(fake_settings(ZHIPUAI_API_KEY="zk"))
        assert cfg.provider == "zhipuai"
        assert cfg.model == "glm-4"
        assert cfg.base_url == "https://open.bigmodel.cn/api/paas/v4/"
        assert cfg.api_key == "zk"

    @pytest.mark.parametrize("tier,expected", [
        ("default", "gpt-4o"), ("fast", "gpt-4o-mini"),
        ("quality", "gpt-4o"), ("light", "gpt-4o-mini"),
    ])
    def test_openai_tiers(self, tier, expected):
        cfg = resolve_llm_config(fake_settings(LLM_PROVIDER="openai"), tier=tier)
        assert cfg.model == expected
        assert cfg.base_url == "https://api.openai.com/v1"

    @pytest.mark.parametrize("tier,expected", [
        ("fast", "glm-4-flash"), ("quality", "glm-4-plus"), ("light", "glm-4-air"),
    ])
    def test_zhipuai_tiers(self, tier, expected):
        assert resolve_llm_config(fake_settings(), tier=tier).model == expected


class TestPrecedence:
    def test_env_model_beats_preset(self):
        cfg = resolve_llm_config(fake_settings(LLM_MODEL_QUALITY="glm-4.5"), tier="quality")
        assert cfg.model == "glm-4.5"

    def test_explicit_arg_beats_env(self):
        cfg = resolve_llm_config(
            fake_settings(LLM_MODEL="env-model"), tier="default", model="arg-model")
        assert cfg.model == "arg-model"

    def test_env_base_url_beats_preset(self):
        cfg = resolve_llm_config(fake_settings(LLM_BASE_URL="http://proxy:9/v1"))
        assert cfg.base_url == "http://proxy:9/v1"

    def test_llm_api_key_beats_zhipuai_key(self):
        cfg = resolve_llm_config(fake_settings(LLM_API_KEY="new", ZHIPUAI_API_KEY="old"))
        assert cfg.api_key == "new"

    def test_zhipuai_key_fallback(self):
        cfg = resolve_llm_config(fake_settings(ZHIPUAI_API_KEY="old"))
        assert cfg.api_key == "old"

    def test_no_keys_resolves_to_empty_string(self):
        # Resolution never raises on missing keys; first LLM use does (Task 2).
        assert resolve_llm_config(fake_settings()).api_key == ""


class TestValidation:
    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="LLM_PROVIDER"):
            resolve_llm_config(fake_settings(LLM_PROVIDER="gemini"))

    def test_unknown_tier_raises(self):
        with pytest.raises(ValueError, match="tier"):
            resolve_llm_config(fake_settings(), tier="turbo")

    def test_provider_case_insensitive(self):
        assert resolve_llm_config(fake_settings(LLM_PROVIDER="OpenAI")).provider == "openai"

    def test_all_tiers_present_in_all_presets(self):
        for preset in PROVIDER_PRESETS.values():
            assert set(preset["models"]) == set(TIERS)
