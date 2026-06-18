# Phase 1b: Generation Evals + LLM Provider Abstraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend LLM layer provider-agnostic (ZhipuAI/OpenAI via env), add LLM-as-judge generation metrics to the eval harness, build the real-codebase golden set, and publish baseline numbers in the README.

**Architecture:** Provider presets + a resolution function feed a renamed `LLMService` (lazy LLM construction, call sites unchanged). The eval harness gains an opt-in generation phase: per case, the existing retrieval output's `combined_context` feeds a fixed RAG prompt, the answer is scored by two reference-free judge calls (faithfulness, answer_relevance), and the reporter grows a generation section. Spec: `docs/superpowers/specs/2026-06-11-evals-phase1b-design.md`.

**Tech Stack:** Python 3.11, FastAPI config via pydantic-settings, langchain-openai `ChatOpenAI`, pytest + pytest-asyncio. No new dependencies.

**Conventions for every task:**
- Backend tests run from `backend-fastapi/`: `python -m pytest tests/<file> -v --no-cov`
- Evals tests run from repo root: `python -m pytest evals/tests/<file> -v`
- Commit messages: repo style (`feat(llm):`, `feat(evals):`, `fix(evals):`, `docs:`). Never add any AI co-author trailer.
- No emojis anywhere.

---

## Known bug being fixed in Task 5 (context for the implementer)

`evals/runner.py::extract_files_from_retrieval` iterates `semantic_results` as a flat chunk list, but `CodeGraphRetriever.retrieve()` stores the raw return of `ChromaDBClient.search_all()` there, which is a dict: `{"functions": [chunk...], "classes": [chunk...]}` (see `backend-fastapi/app/services/code_graph/chromadb_client.py:274-284`). Iterating a dict yields its string keys, which fail the `isinstance(chunk, dict)` guard, so the extracted file list is always empty and every retrieval metric reads 0. Each chunk dict carries `relevance_score` (1 - distance, higher is better, `chromadb_client.py:239`) which is the merge key.

---

### Task 1: LLM provider presets + resolution function

**Files:**
- Create: `backend-fastapi/app/core/llm_config.py`
- Modify: `backend-fastapi/app/core/config.py` (add 7 fields after `ZHIPUAI_API_KEY`, line 68)
- Test: `backend-fastapi/tests/test_llm_provider.py` (new)

- [ ] **Step 1: Add settings fields**

In `backend-fastapi/app/core/config.py`, directly under the `ZHIPUAI_API_KEY: str = ""` line:

```python
    # LLM Provider Configuration
    # LLM_PROVIDER: "zhipuai" (default) or "openai".
    # LLM_API_KEY falls back to ZHIPUAI_API_KEY when empty (backward compat).
    # Empty model/base_url fields resolve to per-provider presets (app/core/llm_config.py).
    LLM_PROVIDER: str = "zhipuai"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    LLM_MODEL_FAST: str = ""
    LLM_MODEL_QUALITY: str = ""
    LLM_MODEL_LIGHT: str = ""
```

- [ ] **Step 2: Write the failing tests**

Create `backend-fastapi/tests/test_llm_provider.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run (from `backend-fastapi/`): `python -m pytest tests/test_llm_provider.py -v --no-cov`
Expected: collection error — `ModuleNotFoundError: No module named 'app.core.llm_config'`

- [ ] **Step 4: Implement `app/core/llm_config.py`**

```python
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
            "default": "glm-4",
            "fast": "glm-4-flash",
            "quality": "glm-4-plus",
            "light": "glm-4-air",
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
    provider = (settings.LLM_PROVIDER or "zhipuai").lower()
    if provider not in PROVIDER_PRESETS:
        raise ValueError(
            f"Unknown LLM_PROVIDER {provider!r}; expected one of {sorted(PROVIDER_PRESETS)}"
        )
    if tier not in TIERS:
        raise ValueError(f"Unknown tier {tier!r}; expected one of {TIERS}")

    preset = PROVIDER_PRESETS[provider]
    return LLMConfig(
        provider=provider,
        base_url=base_url or settings.LLM_BASE_URL or preset["base_url"],
        model=model or getattr(settings, _TIER_ENV_FIELD[tier]) or preset["models"][tier],
        api_key=api_key or settings.LLM_API_KEY or settings.ZHIPUAI_API_KEY or "",
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_llm_provider.py -v --no-cov`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend-fastapi/app/core/config.py backend-fastapi/app/core/llm_config.py backend-fastapi/tests/test_llm_provider.py
git commit -m "feat(llm): provider presets and config resolution (zhipuai/openai)"
```

---

### Task 2: LLMService with lazy initialization

**Files:**
- Modify: `backend-fastapi/app/services/langchain_glm_service.py`
- Modify: `backend-fastapi/tests/test_glm_services.py:101-114` (two tests change semantics)
- Test: append to `backend-fastapi/tests/test_llm_provider.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend-fastapi/tests/test_llm_provider.py`:

```python
from unittest.mock import MagicMock, patch

from app.services.langchain_glm_service import LangChainGLMService, LLMService


class TestLLMServiceLazyInit:
    def _patch_settings(self, monkeypatch, **overrides):
        monkeypatch.setattr(
            "app.services.langchain_glm_service.settings", fake_settings(**overrides)
        )

    def test_construct_without_key_does_not_raise(self, monkeypatch):
        self._patch_settings(monkeypatch)
        svc = LLMService()  # no key anywhere — must not raise here
        assert svc.model == "glm-4"

    def test_first_llm_access_without_key_raises(self, monkeypatch):
        self._patch_settings(monkeypatch)
        svc = LLMService()
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            _ = svc.llm

    def test_llm_built_once_with_resolved_params(self, monkeypatch):
        self._patch_settings(monkeypatch, LLM_PROVIDER="openai", LLM_API_KEY="ok-key")
        with patch("app.services.langchain_glm_service.ChatOpenAI") as ChatOpenAI:
            svc = LLMService(tier="fast", temperature=0.3)
            ChatOpenAI.assert_not_called()  # lazy: nothing at construction
            first = svc.llm
            second = svc.llm
            assert first is second
            ChatOpenAI.assert_called_once_with(
                api_key="ok-key",
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=None,
            )

    def test_tier_quality_zhipuai(self, monkeypatch):
        self._patch_settings(monkeypatch, ZHIPUAI_API_KEY="zk")
        assert LLMService(tier="quality").model == "glm-4-plus"

    def test_alias_is_same_class(self):
        assert LangChainGLMService is LLMService

    def test_explicit_args_still_win(self, monkeypatch):
        self._patch_settings(monkeypatch, ZHIPUAI_API_KEY="zk")
        svc = LLMService(api_key="explicit", model="custom-model")
        assert svc.model == "custom-model"
        assert svc.api_key == "explicit"
```

- [ ] **Step 2: Run new tests to verify they fail**

Run: `python -m pytest tests/test_llm_provider.py::TestLLMServiceLazyInit -v --no-cov`
Expected: FAIL — `ImportError: cannot import name 'LLMService'`

- [ ] **Step 3: Rewrite the service**

Replace the header, constants, `__init__`, and singleton block of
`backend-fastapi/app/services/langchain_glm_service.py`. The five chat methods
(`chat`, `chat_completion`, `chat_with_history`, `stream_chat`, `get_llm`) keep
their bodies — they already reference `self.llm`, which becomes a property.

```python
"""
LLM Service - provider-agnostic LangChain integration.

Both ZhipuAI and OpenAI are reached through the OpenAI-compatible chat
protocol via ChatOpenAI; provider/model/base_url resolve from env config
(see app/core/llm_config.py). Default provider remains ZhipuAI GLM.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.llm_config import resolve_llm_config

# Backward-compat constants (existing imports elsewhere keep working)
ZHIPUAI_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
ZHIPUAI_MODEL = "glm-4"
ZHIPUAI_MODEL_PLUS = "glm-4-plus"
ZHIPUAI_MODEL_AIR = "glm-4-air"
ZHIPUAI_MODEL_FLASH = "glm-4-flash"


class LLMService:
    """Provider-agnostic chat service. LLM construction is deferred to first
    use so the app (and the eval harness) can import this module without any
    API key configured."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tier: str = "default",
    ):
        self._config = resolve_llm_config(
            settings, tier, model=model, base_url=base_url, api_key=api_key
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llm: Optional[ChatOpenAI] = None

    @property
    def model(self) -> str:
        return self._config.model

    @property
    def api_key(self) -> str:
        return self._config.api_key

    @property
    def llm(self) -> ChatOpenAI:
        if self._llm is None:
            if not self._config.api_key:
                raise ValueError(
                    "No LLM API key configured. Set LLM_API_KEY "
                    "(or ZHIPUAI_API_KEY for the zhipuai provider)."
                )
            self._llm = ChatOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                model=self._config.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        return self._llm

    # ... chat / chat_completion / chat_with_history / stream_chat / get_llm
    # bodies are UNCHANGED from the current file — keep them verbatim.
```

Replace the singleton block at the bottom (constructors no longer raise on
missing keys, so import is always safe):

```python
# Global singletons (names preserved; tier mapping per spec section 5.3)
langchain_glm_service = LLMService(tier="default")

glm_service_flash = LLMService(tier="fast")     # fast responses
glm_service_plus = LLMService(tier="quality")   # high quality
glm_service_air = LLMService(tier="light")      # lightweight

# Backward-compat alias
LangChainGLMService = LLMService
```

Note: `LangChainGLMService = LLMService` must appear AFTER the class
definition; remove the old `class LangChainGLMService` name by renaming the
class itself to `LLMService`.

- [ ] **Step 4: Update the two existing tests whose semantics changed**

In `backend-fastapi/tests/test_glm_services.py`, replace
`TestLangChainGLMService.test_requires_api_key` (lines 102-108):

```python
    def test_missing_key_raises_on_first_use(self, monkeypatch):
        from types import SimpleNamespace
        monkeypatch.setattr(
            "app.services.langchain_glm_service.settings",
            SimpleNamespace(
                LLM_PROVIDER="zhipuai", LLM_API_KEY="", LLM_BASE_URL="",
                LLM_MODEL="", LLM_MODEL_FAST="", LLM_MODEL_QUALITY="",
                LLM_MODEL_LIGHT="", ZHIPUAI_API_KEY="",
            ),
        )
        svc = LangChainGLMService()  # construction is now safe
        with pytest.raises(ValueError, match="LLM_API_KEY"):
            _ = svc.llm
```

`test_get_llm_returns_inner_llm` (lines 110-114) still passes unchanged —
the property constructs on first access inside the `patch` context. Verify,
do not modify unless it fails.

- [ ] **Step 5: Run the full backend suite**

Run: `python -m pytest tests/ -v --no-cov -x`
Expected: all PASS (the other LangChain tests patch `ChatOpenAI` and access
the LLM inside the patch context, so lazy construction is transparent to them)

- [ ] **Step 6: Commit**

```bash
git add backend-fastapi/app/services/langchain_glm_service.py backend-fastapi/tests/test_glm_services.py backend-fastapi/tests/test_llm_provider.py
git commit -m "feat(llm): rename to LLMService with lazy init and provider tiers"
```

---

### Task 3: Document the new env vars

**Files:**
- Modify: `backend-fastapi/.env.example` (after the ZHIPUAI_API_KEY block, ~line 36)
- Modify: `README.md` (Environment Variables table, ~line 233)

- [ ] **Step 1: Extend `.env.example`**

After the `ZHIPUAI_API_KEY=your_zhipuai_api_key` line add:

```
# LLM provider switch: zhipuai (default) or openai.
# Empty values resolve to per-provider presets; LLM_API_KEY falls back to ZHIPUAI_API_KEY.
LLM_PROVIDER=zhipuai
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
LLM_MODEL_FAST=
LLM_MODEL_QUALITY=
LLM_MODEL_LIGHT=
```

- [ ] **Step 2: Extend the README env table**

In the `## Configuration` table after the `ZHIPU_API_KEY` row:

```markdown
| `LLM_PROVIDER` | LLM provider: `zhipuai` or `openai` | `zhipuai` |
| `LLM_API_KEY` | Provider API key (falls back to `ZHIPUAI_API_KEY`) | _(unset)_ |
| `LLM_MODEL` | Override default-tier model (else provider preset) | _(unset)_ |
```

- [ ] **Step 3: Commit**

```bash
git add backend-fastapi/.env.example README.md
git commit -m "docs: document LLM provider env vars"
```

---

### Task 4: Judge metrics module (pure functions + retry contract)

**Files:**
- Create: `evals/metrics/judge.py`
- Test: `evals/tests/test_judge.py` (new)
- Modify: `evals/tests/conftest.py` (add FakeLLM)

- [ ] **Step 1: Add FakeLLM to `evals/tests/conftest.py`**

Append:

```python
class FakeLLM:
    """Scripted async chat double. Each call pops the next response; an
    Exception instance in the script is raised instead of returned."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []  # list of (system_prompt, user_prompt, kwargs)

    async def chat(self, system_prompt, user_prompt, **kwargs):
        self.calls.append((system_prompt, user_prompt, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
```

- [ ] **Step 2: Write the failing tests**

Create `evals/tests/test_judge.py`:

```python
"""Judge prompt builders, JSON parser, and the one-retry contract."""
import pytest

from evals.metrics.judge import (
    JUDGE_RETRY_REMINDER,
    build_faithfulness_prompt,
    build_relevance_prompt,
    judge_once,
    parse_judge_response,
)
from .conftest import FakeLLM


class TestParseJudgeResponse:
    def test_clean_json(self):
        score, reasoning = parse_judge_response('{"score": 4, "reasoning": "grounded"}')
        assert score == 4
        assert reasoning == "grounded"

    def test_json_embedded_in_prose(self):
        text = 'Sure! Here is my verdict:\n{"score": 2, "reasoning": "fabricated"}\nThanks.'
        assert parse_judge_response(text) == (2, "fabricated")

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            parse_judge_response("I think it deserves a 4 out of 5.")

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError):
            parse_judge_response('{"score": 4, "reasoning": ')

    @pytest.mark.parametrize("bad", [0, 6, -1, 3.5, "4", True, None])
    def test_score_out_of_contract_raises(self, bad):
        import json
        with pytest.raises(ValueError):
            parse_judge_response(json.dumps({"score": bad, "reasoning": "x"}))

    def test_missing_reasoning_defaults_empty(self):
        assert parse_judge_response('{"score": 5}') == (5, "")


class TestPromptBuilders:
    def test_faithfulness_sees_context_and_answer_not_question(self):
        system, user = build_faithfulness_prompt("CTX_SENTINEL", "ANS_SENTINEL")
        assert "CTX_SENTINEL" in user
        assert "ANS_SENTINEL" in user
        assert "score" in system

    def test_relevance_sees_question_and_answer_not_context(self):
        system, user = build_relevance_prompt("Q_SENTINEL", "ANS_SENTINEL")
        assert "Q_SENTINEL" in user
        assert "ANS_SENTINEL" in user


class TestJudgeOnce:
    @pytest.mark.asyncio
    async def test_first_try_success(self):
        llm = FakeLLM(['{"score": 5, "reasoning": "ok"}'])
        score, reasoning, failed = await judge_once(llm, "sys", "user")
        assert (score, reasoning, failed) == (5, "ok", False)
        assert llm.calls[0][2].get("temperature") == 0.0

    @pytest.mark.asyncio
    async def test_retry_appends_reminder_and_succeeds(self):
        llm = FakeLLM(["not json at all", '{"score": 3, "reasoning": "ok"}'])
        score, reasoning, failed = await judge_once(llm, "sys", "user")
        assert (score, failed) == (3, False)
        assert len(llm.calls) == 2
        assert llm.calls[1][1].endswith(JUDGE_RETRY_REMINDER)

    @pytest.mark.asyncio
    async def test_two_failures_returns_parse_error(self):
        llm = FakeLLM(["garbage", "more garbage"])
        score, reasoning, failed = await judge_once(llm, "sys", "user")
        assert (score, reasoning, failed) == (None, None, True)

    @pytest.mark.asyncio
    async def test_api_exception_propagates(self):
        llm = FakeLLM([RuntimeError("boom")])
        with pytest.raises(RuntimeError):
            await judge_once(llm, "sys", "user")
```

- [ ] **Step 3: Run tests to verify they fail**

Run (repo root): `python -m pytest evals/tests/test_judge.py -v`
Expected: collection error — no module `evals.metrics.judge`

- [ ] **Step 4: Implement `evals/metrics/judge.py`**

```python
"""LLM-as-judge metrics: faithfulness and answer_relevance.

Reference-free, 1-5 integer scale, strict JSON contract with exactly one
retry (spec section 7.2/7.3). Each judge is deliberately blind to one input:
faithfulness never sees the question; relevance never sees the context.
"""
import json
import re
from typing import Optional, Tuple

JUDGE_RETRY_REMINDER = (
    '\n\nReturn ONLY a JSON object: {"score": <integer 1-5>, '
    '"reasoning": "<short reason>"}. No other text.'
)

_FAITHFULNESS_SYSTEM = (
    "You are a strict evaluator. You receive CODE CONTEXT retrieved from a "
    "codebase and an ANSWER produced by an assistant. Judge ONLY whether every "
    "technical claim in the ANSWER is supported by the CODE CONTEXT. Ignore "
    "style and completeness. 5 = every claim grounded in the context; "
    "3 = minor unsupported details; 1 = largely fabricated. "
    'Respond with ONLY a JSON object: {"score": <integer 1-5>, '
    '"reasoning": "<short reason>"}.'
)

_RELEVANCE_SYSTEM = (
    "You are a strict evaluator. You receive a QUESTION and an ANSWER. Judge "
    "ONLY whether the ANSWER directly addresses the QUESTION. Ignore factual "
    "correctness. 5 = fully on-topic and responsive; 3 = partially addresses "
    "it; 1 = off-topic or evasive. "
    'Respond with ONLY a JSON object: {"score": <integer 1-5>, '
    '"reasoning": "<short reason>"}.'
)


def build_faithfulness_prompt(context: str, answer: str) -> Tuple[str, str]:
    return _FAITHFULNESS_SYSTEM, f"CODE CONTEXT:\n{context}\n\nANSWER:\n{answer}"


def build_relevance_prompt(question: str, answer: str) -> Tuple[str, str]:
    return _RELEVANCE_SYSTEM, f"QUESTION:\n{question}\n\nANSWER:\n{answer}"


def parse_judge_response(text: str) -> Tuple[int, str]:
    """Extract and validate the judge JSON. Raises ValueError on any
    violation. Scores outside 1-5 (or non-int, incl. bool) are rejected, not
    clamped — the contract stays strict."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in judge response")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"judge response is not valid JSON: {exc}") from exc
    score = data.get("score")
    if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
        raise ValueError(f"judge score violates contract: {score!r}")
    return score, str(data.get("reasoning", ""))


async def judge_once(llm, system: str, user: str) -> Tuple[Optional[int], Optional[str], bool]:
    """One judge call with one retry on parse failure.

    Returns (score, reasoning, parse_failed). API/network exceptions
    propagate — the caller decides error semantics (spec section 8).
    """
    text = await llm.chat(system, user, temperature=0.0)
    try:
        score, reasoning = parse_judge_response(text)
        return score, reasoning, False
    except ValueError:
        pass
    text = await llm.chat(system, user + JUDGE_RETRY_REMINDER, temperature=0.0)
    try:
        score, reasoning = parse_judge_response(text)
        return score, reasoning, False
    except ValueError:
        return None, None, True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest evals/tests/test_judge.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add evals/metrics/judge.py evals/tests/test_judge.py evals/tests/conftest.py
git commit -m "feat(evals): LLM-as-judge faithfulness and relevance with strict JSON contract"
```

---

### Task 5: Fix the semantic_results dict-shape bug

**Files:**
- Modify: `evals/runner.py:43-63` (`extract_files_from_retrieval`)
- Test: `evals/tests/test_runner_extract.py` (new)

- [ ] **Step 1: Write the failing test**

Create `evals/tests/test_runner_extract.py`:

```python
"""extract_files_from_retrieval must handle search_all()'s actual dict shape:
{"functions": [chunk...], "classes": [chunk...]} merged by relevance_score."""
from evals.runner import extract_files_from_retrieval


def chunk(path, score):
    return {"metadata": {"module_path": path}, "relevance_score": score}


class TestDictShape:
    def test_dict_shape_extracts_and_ranks_by_relevance(self):
        semantic_results = {
            "functions": [chunk("app/a.py", 0.9), chunk("app/c.py", 0.5)],
            "classes": [chunk("app/b.py", 0.7)],
        }
        assert extract_files_from_retrieval(semantic_results) == [
            "app/a.py", "app/b.py", "app/c.py",
        ]

    def test_empty_dict(self):
        assert extract_files_from_retrieval({}) == []

    def test_missing_relevance_score_sorts_last(self):
        semantic_results = {
            "functions": [{"metadata": {"module_path": "app/x.py"}}],
            "classes": [chunk("app/y.py", 0.1)],
        }
        assert extract_files_from_retrieval(semantic_results) == ["app/y.py", "app/x.py"]


class TestListShapeStillWorks:
    def test_flat_list_passthrough(self):
        flat = [chunk("app/a.py", 0.9), chunk("backend-fastapi/app/b.py", 0.8)]
        assert extract_files_from_retrieval(flat) == ["app/a.py", "app/b.py"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest evals/tests/test_runner_extract.py -v`
Expected: `TestDictShape` cases FAIL (extraction returns `[]`);
`TestListShapeStillWorks` PASSES

- [ ] **Step 3: Implement the fix**

In `evals/runner.py`, insert before `extract_files_from_retrieval` and adjust
its head:

```python
def _flatten_semantic_results(semantic_results) -> list[dict]:
    """search_all() returns {"functions": [...], "classes": [...]}; merge the
    per-collection lists into one ranking by relevance_score (descending,
    chromadb_client.py:239 — higher is better). Flat lists (unit fixtures and
    any future pre-merged source) pass through with non-dict items dropped."""
    if isinstance(semantic_results, dict):
        merged = []
        for chunks in semantic_results.values():
            if isinstance(chunks, list):
                merged.extend(c for c in chunks if isinstance(c, dict))
        merged.sort(key=lambda c: c.get("relevance_score", 0), reverse=True)
        return merged
    return [c for c in semantic_results if isinstance(c, dict)]


def extract_files_from_retrieval(semantic_results) -> list[str]:
    """Extract chunk file paths in rank order.

    Accepts either search_all()'s dict shape (merged by relevance_score via
    _flatten_semantic_results) or a pre-flattened chunk list.

    Per TBD #1 (resolved Section 16 of the v1 spec): each chunk stores its
    path under ``metadata.module_path``. The storage layer applies no
    normalization — the harness strips a leading ``backend-fastapi/`` so
    paths line up with golden cases' ``app/...`` convention.
    """
    files: list[str] = []
    for chunk in _flatten_semantic_results(semantic_results):
        metadata = chunk.get("metadata") or {}
        module_path = metadata.get("module_path")
        if not module_path:
            continue
        if module_path.startswith("backend-fastapi/"):
            module_path = module_path[len("backend-fastapi/"):]
        files.append(module_path)
    return files
```

The old signature was `(semantic_results: Sequence[dict])`; it is now
untyped (accepts dict or list). If `Sequence` becomes unused in
`evals/runner.py` imports after this change, remove it from the
`typing` import line.

- [ ] **Step 4: Run the full evals suite**

Run: `python -m pytest evals/tests/ -v`
Expected: all PASS (existing tests pass flat lists — still supported)

- [ ] **Step 5: Commit**

```bash
git add evals/runner.py evals/tests/test_runner_extract.py
git commit -m "fix(evals): handle search_all dict shape; retrieval metrics no longer read 0"
```

---

### Task 6: Generation chain module

**Files:**
- Create: `evals/generation.py`
- Test: `evals/tests/test_generation.py` (new)

- [ ] **Step 1: Write the failing tests**

Create `evals/tests/test_generation.py`:

```python
"""RAG generation chain: prompt assembly and the generate-then-judge flow."""
import pytest

from evals.generation import (
    GEN_PROMPT_VERSION,
    MAX_CONTEXT_CHARS,
    GenerationResult,
    build_gen_prompt,
    generate_and_judge,
)
from .conftest import FakeLLM

GOOD_JUDGE = '{"score": 4, "reasoning": "ok"}'


class TestBuildGenPrompt:
    def test_contains_question_and_context(self):
        system, user = build_gen_prompt("How does auth work?", "def login(): ...")
        assert "How does auth work?" in user
        assert "def login(): ..." in user
        assert "code context" in system.lower()

    def test_context_truncated_to_limit(self):
        _, user = build_gen_prompt("q", "x" * (MAX_CONTEXT_CHARS + 500))
        assert len(user) < MAX_CONTEXT_CHARS + 200  # context capped + scaffold

    def test_none_context_treated_as_empty(self):
        _, user = build_gen_prompt("q", None)
        assert "QUESTION:" in user

    def test_prompt_version_pinned(self):
        assert GEN_PROMPT_VERSION == "v1"


class TestGenerateAndJudge:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        gen_llm = FakeLLM(["The login flow uses JWT."])
        judge_llm = FakeLLM([GOOD_JUDGE, '{"score": 5, "reasoning": "on topic"}'])
        result = await generate_and_judge("How does auth work?", "ctx", gen_llm, judge_llm)
        assert result.answer == "The login flow uses JWT."
        assert result.faithfulness == 4
        assert result.answer_relevance == 5
        assert result.error is None
        assert result.judge_parse_errors == 0
        # faithfulness judge saw the context, relevance judge saw the question
        assert "ctx" in judge_llm.calls[0][1]
        assert "How does auth work?" in judge_llm.calls[1][1]

    @pytest.mark.asyncio
    async def test_generation_failure_short_circuits(self):
        gen_llm = FakeLLM([RuntimeError("api down")])
        judge_llm = FakeLLM([])
        result = await generate_and_judge("q", "ctx", gen_llm, judge_llm)
        assert result.error.startswith("generation:")
        assert result.faithfulness is None
        assert judge_llm.calls == []

    @pytest.mark.asyncio
    async def test_judge_failure_keeps_answer(self):
        gen_llm = FakeLLM(["answer"])
        judge_llm = FakeLLM([RuntimeError("judge down")])
        result = await generate_and_judge("q", "ctx", gen_llm, judge_llm)
        assert result.answer == "answer"
        assert result.error.startswith("judge:")

    @pytest.mark.asyncio
    async def test_parse_errors_counted_not_fatal(self):
        gen_llm = FakeLLM(["answer"])
        judge_llm = FakeLLM(["junk", "junk", GOOD_JUDGE])  # faith fails twice, rel ok
        result = await generate_and_judge("q", "ctx", gen_llm, judge_llm)
        assert result.faithfulness is None
        assert result.answer_relevance == 4
        assert result.judge_parse_errors == 1
        assert result.error is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest evals/tests/test_generation.py -v`
Expected: collection error — no module `evals.generation`

- [ ] **Step 3: Implement `evals/generation.py`**

```python
"""Minimal RAG generation chain under evaluation (spec section 7).

The prompt is versioned and frozen: Phase 2 retrieval changes must keep
GEN_PROMPT_VERSION untouched so generation-metric deltas are attributable
to retrieval, not prompt drift.
"""
from dataclasses import dataclass, field
from typing import Optional

GEN_PROMPT_VERSION = "v1"

GEN_SYSTEM_PROMPT = (
    "You are a code assistant answering questions about a Python codebase. "
    "Answer using ONLY the provided code context. If the context is "
    "insufficient, say so explicitly instead of guessing. Be concise and "
    "reference concrete file paths and symbol names."
)

# Keep the prompt within model context limits; combined_context is plain text
# assembled by the retriever, truncate the tail beyond this budget.
MAX_CONTEXT_CHARS = 12000


def build_gen_prompt(question: str, context: Optional[str]) -> tuple[str, str]:
    context = (context or "")[:MAX_CONTEXT_CHARS]
    return GEN_SYSTEM_PROMPT, f"CODE CONTEXT:\n{context}\n\nQUESTION:\n{question}"


@dataclass
class GenerationResult:
    answer: str = ""
    faithfulness: Optional[int] = None
    faithfulness_reasoning: Optional[str] = None
    answer_relevance: Optional[int] = None
    answer_relevance_reasoning: Optional[str] = None
    judge_parse_errors: int = 0
    error: Optional[str] = None


async def generate_and_judge(question, combined_context, gen_llm, judge_llm) -> GenerationResult:
    """Generate an answer from the retrieved context, then score it with two
    blind judges. Generation failure short-circuits (nothing to judge); judge
    failure preserves the answer. Parse failures are counted, never fatal."""
    from evals.metrics.judge import (
        build_faithfulness_prompt,
        build_relevance_prompt,
        judge_once,
    )

    try:
        system, user = build_gen_prompt(question, combined_context)
        answer = await gen_llm.chat(system, user, temperature=0.0)
    except Exception as exc:
        return GenerationResult(error=f"generation: {type(exc).__name__}: {exc}")

    result = GenerationResult(answer=answer)
    try:
        system, user = build_faithfulness_prompt(combined_context or "", answer)
        score, reasoning, failed = await judge_once(judge_llm, system, user)
        result.faithfulness, result.faithfulness_reasoning = score, reasoning
        result.judge_parse_errors += int(failed)

        system, user = build_relevance_prompt(question, answer)
        score, reasoning, failed = await judge_once(judge_llm, system, user)
        result.answer_relevance, result.answer_relevance_reasoning = score, reasoning
        result.judge_parse_errors += int(failed)
    except Exception as exc:
        result.error = f"judge: {type(exc).__name__}: {exc}"
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest evals/tests/test_generation.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add evals/generation.py evals/tests/test_generation.py
git commit -m "feat(evals): RAG generation chain with versioned prompt and blind judges"
```

---

### Task 7: Runner — carry context, add the generation phase

**Files:**
- Modify: `evals/runner.py` (CaseResult fields, `run_one_case`, new `run_generation_phase`)
- Modify: `evals/config.py` (add `DEFAULT_GEN_TIMEOUT_S`)
- Test: `evals/tests/test_runner_generation.py` (new)

- [ ] **Step 1: Add the config constant**

In `evals/config.py` after `DEFAULT_PER_CASE_TIMEOUT_S`:

```python
DEFAULT_GEN_TIMEOUT_S = 120.0  # per-case generation + 2 judge calls budget
```

- [ ] **Step 2: Write the failing tests**

Create `evals/tests/test_runner_generation.py`:

```python
"""run_generation_phase: annotates CaseResults in place, skips errored cases."""
import pytest

from evals.runner import CaseResult, run_generation_phase
from .conftest import FakeLLM

GOOD_JUDGE = '{"score": 4, "reasoning": "ok"}'


def make_result(case_id="c1", error=None, question="q?", context="ctx"):
    return CaseResult(
        id=case_id, category="definition_lookup", expected_files=["app/a.py"],
        expected_graph_neighbors=None, question=question,
        combined_context=context, error=error,
    )


class TestRunGenerationPhase:
    @pytest.mark.asyncio
    async def test_annotates_each_case(self):
        results = [make_result("c1"), make_result("c2")]
        gen_llm = FakeLLM(["a1", "a2"])
        judge_llm = FakeLLM([GOOD_JUDGE] * 4)
        await run_generation_phase(results, gen_llm, judge_llm, concurrency=1, timeout_s=30)
        assert all(r.generation is not None for r in results)
        assert results[0].generation.faithfulness == 4

    @pytest.mark.asyncio
    async def test_retrieval_errored_case_skipped(self):
        results = [make_result("bad", error="timeout")]
        gen_llm = FakeLLM([])
        judge_llm = FakeLLM([])
        await run_generation_phase(results, gen_llm, judge_llm, concurrency=1, timeout_s=30)
        assert results[0].generation.error.startswith("skipped:")
        assert gen_llm.calls == []

    @pytest.mark.asyncio
    async def test_timeout_recorded_per_case(self):
        import asyncio

        class SlowLLM:
            async def chat(self, *a, **k):
                await asyncio.sleep(5)
                return "late"

        results = [make_result("slow")]
        await run_generation_phase(results, SlowLLM(), FakeLLM([]), concurrency=1, timeout_s=0.05)
        assert results[0].generation.error == "timeout"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest evals/tests/test_runner_generation.py -v`
Expected: FAIL — `CaseResult` has no `question` field / no `run_generation_phase`

- [ ] **Step 4: Implement runner changes**

In `evals/runner.py`:

(a) Extend `CaseResult` (the dataclass at line 19) with three fields placed
after `expected_graph_neighbors`:

```python
    question: str = ""
    combined_context: str = ""
    generation: Optional[Any] = None  # GenerationResult when --with-generation
```

(b) In `run_one_case`, populate them. The two early-return error branches
gain `question=case["question"]`; the success return becomes:

```python
    return CaseResult(
        id=case["id"], category=case["category"],
        expected_files=expected_files,
        expected_graph_neighbors=expected_neighbors,
        question=case["question"],
        combined_context=raw.get("combined_context") or "",
        retrieved_files_ranked=retrieved_files,
        retrieved_graph_neighbors=retrieved_neighbors,
        metrics=metrics,
    )
```

(c) Append the generation phase:

```python
async def run_generation_phase(
    results: list[CaseResult],
    gen_llm,
    judge_llm,
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    timeout_s: float = 120.0,
) -> None:
    """Annotate each CaseResult.generation in place. Cases whose retrieval
    errored are skipped (no context to generate from); their retrieval error
    is preserved and the skip is recorded. Per-case budget covers generation
    plus both judge calls (spec section 7.4)."""
    from evals.generation import GenerationResult, generate_and_judge

    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(r: CaseResult) -> None:
        if r.error:
            r.generation = GenerationResult(error=f"skipped: retrieval error ({r.error})")
            return
        async with semaphore:
            try:
                r.generation = await asyncio.wait_for(
                    generate_and_judge(r.question, r.combined_context, gen_llm, judge_llm),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                r.generation = GenerationResult(error="timeout")
            except Exception as exc:
                r.generation = GenerationResult(error=f"{type(exc).__name__}: {exc}")

    await asyncio.gather(*(bounded(r) for r in results))
```

- [ ] **Step 5: Run the full evals suite**

Run: `python -m pytest evals/tests/ -v`
Expected: all PASS (new CaseResult fields are defaulted, existing
constructions unaffected)

- [ ] **Step 6: Commit**

```bash
git add evals/runner.py evals/config.py evals/tests/test_runner_generation.py
git commit -m "feat(evals): generation phase over retrieval results with per-case budget"
```

---

### Task 8: Reporter — generation aggregate, table section, JSON block

**Files:**
- Modify: `evals/reporter.py`
- Test: extend `evals/tests/test_reporter.py`

- [ ] **Step 1: Write the failing tests**

Append to `evals/tests/test_reporter.py` (reuse its existing fixture style;
import `GenerationResult` from `evals.generation` and `CaseResult` from
`evals.runner`):

```python
from evals.generation import GenerationResult
from evals.reporter import compute_generation_aggregate


def _gen_case(case_id, faith, rel, *, error=None, parse_errors=0):
    from evals.runner import CaseResult
    return CaseResult(
        id=case_id, category="definition_lookup", expected_files=["app/a.py"],
        expected_graph_neighbors=None,
        generation=GenerationResult(
            answer="a", faithfulness=faith, answer_relevance=rel,
            judge_parse_errors=parse_errors, error=error,
        ),
    )


class TestComputeGenerationAggregate:
    def test_no_generation_returns_none(self):
        from evals.runner import CaseResult
        plain = CaseResult(id="x", category="definition_lookup",
                           expected_files=[], expected_graph_neighbors=None)
        assert compute_generation_aggregate([plain]) is None

    def test_means_and_pct_ge_4(self):
        cases = [_gen_case("a", 5, 4), _gen_case("b", 3, 2), _gen_case("c", 4, 5)]
        agg = compute_generation_aggregate(cases)
        assert agg["n"] == 3
        assert agg["faithfulness"] == 4.0
        assert agg["faithfulness_pct_ge_4"] == round(2 / 3, 4)
        assert agg["answer_relevance_pct_ge_4"] == round(2 / 3, 4)

    def test_errors_and_nulls_excluded_from_means(self):
        cases = [
            _gen_case("ok", 5, 5),
            _gen_case("err", None, None, error="generation: boom"),
            _gen_case("parse", None, 4, parse_errors=1),
        ]
        agg = compute_generation_aggregate(cases)
        assert agg["n"] == 3
        assert agg["gen_errors"] == 1
        assert agg["gen_error_rate"] == round(1 / 3, 4)
        assert agg["judge_parse_errors"] == 1
        assert agg["faithfulness"] == 5.0       # only the one non-null value
        assert agg["faithfulness_n"] == 1
        assert agg["answer_relevance_n"] == 2

    def test_by_category_breakdown(self):
        cases = [_gen_case("a", 5, 4), _gen_case("b", 3, 2)]
        agg = compute_generation_aggregate(cases)
        cat = agg["by_category"]["definition_lookup"]
        assert cat["n"] == 2
        assert cat["faithfulness"] == 4.0
        assert cat["answer_relevance"] == 3.0


class TestGenerationTableSection:
    def test_render_includes_generation_when_present(self):
        from evals.reporter import render_table
        aggregate = {
            "overall": {"n": 2, "errors": 0, "hit_rate@5": 0.5},
            "by_category": {},
            "generation": {
                "n": 2, "gen_errors": 0, "gen_error_rate": 0.0,
                "judge_parse_errors": 0,
                "faithfulness": 4.5, "faithfulness_pct_ge_4": 1.0, "faithfulness_n": 2,
                "answer_relevance": 4.0, "answer_relevance_pct_ge_4": 0.5,
                "answer_relevance_n": 2,
            },
        }
        out = render_table(aggregate)
        assert "==== Generation" in out
        assert "faithfulness" in out

    def test_render_unchanged_without_generation(self):
        from evals.reporter import render_table
        aggregate = {"overall": {"n": 1, "errors": 0, "hit_rate@5": 1.0}, "by_category": {}}
        assert "Generation" not in render_table(aggregate)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest evals/tests/test_reporter.py -v`
Expected: new tests FAIL (`compute_generation_aggregate` missing); existing PASS

- [ ] **Step 3: Implement reporter changes**

In `evals/reporter.py`:

(a) New function after `compute_aggregate`:

```python
_GEN_METRIC_KEYS = ("faithfulness", "answer_relevance")


def compute_generation_aggregate(case_results: Iterable[Any]) -> "dict | None":
    """Aggregate GenerationResults, overall and per category (spec 7.3).
    Returns None when no case carries one (retrieval-only runs keep their
    JSON byte-identical to v1). Null scores are excluded from means;
    per-metric sample size is reported."""
    annotated = [r for r in case_results if getattr(r, "generation", None) is not None]
    if not annotated:
        return None
    gens = [r.generation for r in annotated]
    n = len(gens)
    gen_errors = sum(1 for g in gens if g.error)
    block: dict[str, Any] = {
        "n": n,
        "gen_errors": gen_errors,
        "gen_error_rate": round(gen_errors / n, 4),
        "judge_parse_errors": sum(g.judge_parse_errors for g in gens),
    }
    for key in _GEN_METRIC_KEYS:
        values = [getattr(g, key) for g in gens if getattr(g, key) is not None]
        if values:
            block[key] = round(sum(values) / len(values), 4)
            block[f"{key}_pct_ge_4"] = round(sum(1 for v in values if v >= 4) / len(values), 4)
            block[f"{key}_n"] = len(values)

    by_category: dict[str, dict] = {}
    cat_cases: dict[str, list] = defaultdict(list)
    for r in annotated:
        cat_cases[r.category].append(r.generation)
    for cat, cat_gens in cat_cases.items():
        cat_block: dict[str, Any] = {"n": len(cat_gens)}
        for key in _GEN_METRIC_KEYS:
            values = [getattr(g, key) for g in cat_gens if getattr(g, key) is not None]
            if values:
                cat_block[key] = round(sum(values) / len(values), 4)
        by_category[cat] = cat_block
    block["by_category"] = by_category
    return block
```

(`defaultdict` is already imported in reporter.py.)

(b) In `render_table`, before the final `return`:

```python
    gen = aggregate.get("generation")
    if gen:
        lines.append("")
        lines.append(
            f"==== Generation (n={gen['n']}, gen_errors={gen['gen_errors']}, "
            f"judge_parse_errors={gen['judge_parse_errors']}) ===="
        )
        for key in _GEN_METRIC_KEYS:
            if key in gen:
                lines.append(
                    f"{key:<28}  {gen[key]}  (>=4: {gen[f'{key}_pct_ge_4']:.0%}, "
                    f"n={gen[f'{key}_n']})"
                )
```

(c) In `write_json`, the per-case dict gains one entry (after `"error"`):

```python
                "generation": (
                    None if getattr(r, "generation", None) is None
                    else asdict(r.generation)
                ),
```

Add `from dataclasses import asdict` to the imports.

- [ ] **Step 4: Run the evals suite**

Run: `python -m pytest evals/tests/ -v`
Expected: all PASS (including the existing snapshot test — table output
without generation data is unchanged)

- [ ] **Step 5: Commit**

```bash
git add evals/reporter.py evals/tests/test_reporter.py
git commit -m "feat(evals): generation aggregate, table section, and JSON block"
```

---

### Task 9: CLI wiring for --with-generation

**Files:**
- Modify: `evals/run.py` (`parse_args`, `main_async`)

- [ ] **Step 1: Add CLI flags**

In `parse_args` (after `--quiet`):

```python
    p.add_argument("--with-generation", action="store_true",
                   help="Generate answers and run LLM-as-judge metrics "
                        "(requires LLM_API_KEY or ZHIPUAI_API_KEY)")
    p.add_argument("--gen-model", type=str, default=None,
                   help="Override generator model (default: provider 'default' tier)")
    p.add_argument("--judge-model", type=str, default=None,
                   help="Override judge model (default: provider 'quality' tier)")
    p.add_argument("--gen-timeout", type=float, default=DEFAULT_GEN_TIMEOUT_S,
                   help="Per-case generation+judge budget in seconds")
```

Import `DEFAULT_GEN_TIMEOUT_S` from `evals.config`.

- [ ] **Step 2: Early API-key check in `main_async`**

Immediately after the golden-set validation block (before indexing, per spec
section 8 "before any case runs"):

```python
    gen_llm = judge_llm = None
    if args.with_generation:
        from app.core.config import settings
        if not (settings.LLM_API_KEY or settings.ZHIPUAI_API_KEY):
            print("ERROR: --with-generation requires LLM_API_KEY or "
                  "ZHIPUAI_API_KEY to be configured", file=sys.stderr)
            return 2
        from app.services.langchain_glm_service import LLMService
        gen_llm = (LLMService(model=args.gen_model) if args.gen_model
                   else LLMService(tier="default"))
        judge_llm = (LLMService(model=args.judge_model) if args.judge_model
                     else LLMService(tier="quality"))
```

- [ ] **Step 3: Run the phase and extend meta/aggregate**

After the `run_corpus` call:

```python
    if args.with_generation:
        from evals.runner import run_generation_phase
        await run_generation_phase(
            results, gen_llm, judge_llm,
            concurrency=args.concurrency, timeout_s=args.gen_timeout,
        )
```

In `meta["config"]` add:

```python
            "with_generation": args.with_generation,
            "gen_model": gen_llm.model if gen_llm else None,
            "judge_model": judge_llm.model if judge_llm else None,
            "gen_prompt_version": GEN_PROMPT_VERSION if args.with_generation else None,
```

with a guarded import at the top of the file:
`from evals.generation import GEN_PROMPT_VERSION`.

After `aggregate = compute_aggregate(results)`:

```python
    gen_aggregate = compute_generation_aggregate(results)
    if gen_aggregate is not None:
        aggregate["generation"] = gen_aggregate
```

Import `compute_generation_aggregate` alongside the existing reporter imports.

- [ ] **Step 4: Verify default behavior is unchanged and flags parse**

Run (repo root):
- `python -m evals.run --help` — shows the four new flags
- `python -m pytest evals/tests/ -v` — all PASS
- `python -c "from evals.run import parse_args; a = parse_args(['--golden','x.jsonl','--with-generation','--gen-timeout','60']); print(a.with_generation, a.gen_timeout)"` — prints `True 60.0`

- [ ] **Step 5: Commit**

```bash
git add evals/run.py
git commit -m "feat(evals): --with-generation CLI with early key check and meta provenance"
```

---

### Task 10: Golden set draft (~50 candidates)

**Files:**
- Create: `evals/golden_set/backend_fastapi.draft.jsonl`

This is a content-authoring task, not a coding task. Method (spec section 6,
v1 workflow):

- [ ] **Step 1: Survey the corpus**

Read every module under `backend-fastapi/app/` (api/, core/, models/,
schemas/, services/, services/code_graph/). For each, note 2-4 askable facts:
what is defined there (definition_lookup), what feature it implements
(feature_lookup), what it imports/calls (dependency_trace), what breaks if it
changes (impact_analysis), and which multi-file flows it participates in
(cross_file_flow).

- [ ] **Step 2: Author the draft cases**

Write ~50 JSONL cases with this category distribution: definition_lookup 12,
feature_lookup 12, dependency_trace 10, impact_analysis 8, cross_file_flow 8.
Schema (v1, unchanged — no reference_answer field):

```json
{"id": "jwt-refresh-001", "question": "Where is the JWT refresh token lifetime configured and what is the default?", "category": "definition_lookup", "expected_files": ["app/core/config.py"], "expected_symbols": ["REFRESH_TOKEN_EXPIRE_DAYS"], "expected_graph_neighbors": null, "notes": "Settings.REFRESH_TOKEN_EXPIRE_DAYS = 7"}
```

Rules:
- `expected_files` paths are `app/`-relative and MUST exist in the working tree — open each file and confirm the symbol before writing the case
- `expected_graph_neighbors` use bare unqualified names (e.g. `"CodeGraphRetriever"`, never dotted paths) and are optional — only fill them where imports/call sites are statically obvious; otherwise `null`
- questions are natural English a developer would ask, no file names leaked into the question for definition/feature categories (that would make retrieval trivial)
- ids are stable kebab-case slugs

- [ ] **Step 3: Validate**

Run (repo root):

```bash
python -c "from pathlib import Path; from evals.golden_set.validate import validate_golden_set; errs, warns = validate_golden_set(Path('evals/golden_set/backend_fastapi.draft.jsonl'), Path('.')); print('\n'.join(errs + warns) or 'OK'); raise SystemExit(1 if errs else 0)"
```

Expected: `OK` or warnings only (missing optional fields warn, not fail)

- [ ] **Step 4: Commit**

```bash
git add evals/golden_set/backend_fastapi.draft.jsonl
git commit -m "feat(evals): draft golden set for backend-fastapi corpus (50 candidates)"
```

---

### Task 11: CHECKPOINT — human review of the golden set

**Files:**
- Create: `evals/golden_set/backend_fastapi.jsonl` (the reviewed keeper set)

- [ ] **Step 1: Present the draft to the user for review**

STOP and ask the user to review `backend_fastapi.draft.jsonl`: trim bad
cases, fix questions/expectations, keep 30-50. Do not proceed to Task 12
until the user confirms the final set.

- [ ] **Step 2: Save the reviewed set and validate**

Copy the approved cases to `evals/golden_set/backend_fastapi.jsonl`, re-run
the validation snippet from Task 10 Step 3 against the final path.
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add evals/golden_set/backend_fastapi.jsonl
git commit -m "feat(evals): reviewed golden set for backend-fastapi (final)"
```

---

### Task 12: Baseline runs + README Evaluation section

**Files:**
- Modify: `README.md` (new `## Evaluation` section after `## Performance`; fix the LangGraph row in Tech Stack, line 55)

Prerequisites (user environment): Docker services up (`docker compose up -d`),
`ZHIPUAI_API_KEY` set in `backend-fastapi/.env`.

- [ ] **Step 1: Index the corpus into the eval project**

Run (repo root):

```bash
python -m evals.run --golden evals/golden_set/backend_fastapi.jsonl --index-corpus backend-fastapi/app
```

Note: `_do_index` stores paths relative to the corpus parent, so
`backend-fastapi/app/...` files index as `app/...` — matching the golden
set convention. This run also produces the retrieval-only baseline.
Expected: table printed, JSON written to `evals/results/`.

- [ ] **Step 2: Run the generation baseline**

```bash
python -m evals.run --golden evals/golden_set/backend_fastapi.jsonl --with-generation
```

Expected: same retrieval numbers (index unchanged) plus the
`==== Generation ====` section. Budget ~10-20 min and a few RMB of GLM
calls. If `gen_error_rate` > 0.2, investigate before publishing numbers.

- [ ] **Step 3: Write the README Evaluation section**

Insert after the `## Performance` section:

```markdown
## Evaluation

The repo ships a runnable eval harness (`evals/`) measuring the GraphRAG
pipeline on a golden set of N questions about this codebase (replace N and
all numbers below from the actual baseline JSON in `evals/results/`).

### Retrieval (golden set, git <sha>, <date>)

| Metric | Value |
|---|---:|
| hit_rate@5 | 0.00 |
| recall@5 | 0.00 |
| mrr | 0.00 |
| graph_neighbor_recall | 0.00 |
| hybrid_hit_rate@5 | 0.00 |

### Generation (GLM-4 generator, GLM-4-plus judge, prompt v1)

| Metric | Mean (1-5) | Share >= 4 |
|---|---:|---:|
| faithfulness | 0.0 | 0% |
| answer_relevance | 0.0 | 0% |

Reproduce: `docker compose up -d`, index once with `--index-corpus
backend-fastapi/app`, then `python -m evals.run --golden
evals/golden_set/backend_fastapi.jsonl --with-generation`. Generation evals
are opt-in and never run in CI (retrieval-only smoke runs on every PR).
The eval index lives under `project_id=99999`, isolated from dev data in
ChromaDB (Neo4j read isolation is a known limitation, see the v1 design doc).

Judge limitation: generator and judge are same-family models (GLM) by
default; the provider abstraction (`LLM_PROVIDER=openai`) allows re-judging
with a disjoint model family as a cross-check.
```

Fill every `0.00` placeholder from the actual result JSON before committing.

- [ ] **Step 4: Fix the Tech Stack honesty issue**

In the README Tech Stack table change:

`| AI/LLM | LangChain, LangGraph, ZhipuAI GLM-4 |`

to:

`| AI/LLM | LangChain, ZhipuAI GLM-4 / OpenAI (switchable provider); LangGraph agent rewrite planned |`

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README evaluation section with baseline numbers; tech stack accuracy fix"
```

---

## Verification (whole plan)

From repo root after all tasks:

```bash
cd backend-fastapi && python -m pytest tests/ --no-cov -q && cd ..
python -m pytest evals/tests/ -q
python -m evals.run --help
```

Expected: both suites green; help shows `--with-generation`. CI (push) must
stay green: the `evals-smoke` job runs retrieval-only and is unaffected by
generation features; the `backend` job picks up the new provider tests.
