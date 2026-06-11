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
    async def test_second_judge_exception_keeps_first_score(self):
        gen_llm = FakeLLM(["answer"])
        # faithfulness succeeds, relevance raises
        judge_llm = FakeLLM([GOOD_JUDGE, RuntimeError("relevance down")])
        result = await generate_and_judge("q", "ctx", gen_llm, judge_llm)
        assert result.answer == "answer"
        assert result.faithfulness == 4
        assert result.answer_relevance is None
        assert result.error.startswith("judge:")

    @pytest.mark.asyncio
    async def test_parse_errors_counted_not_fatal(self):
        gen_llm = FakeLLM(["answer"])
        # faithfulness exhausts both judge_once attempts (initial + retry),
        # relevance succeeds on its first call
        judge_llm = FakeLLM(["junk", "junk", GOOD_JUDGE])
        result = await generate_and_judge("q", "ctx", gen_llm, judge_llm)
        assert result.faithfulness is None
        assert result.answer_relevance == 4
        assert result.judge_parse_errors == 1
        assert result.error is None
