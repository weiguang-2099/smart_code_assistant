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
