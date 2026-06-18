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
