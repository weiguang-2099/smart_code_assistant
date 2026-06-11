"""Minimal RAG generation chain under evaluation (spec section 7).

The prompt is versioned and frozen: Phase 2 retrieval changes must keep
GEN_PROMPT_VERSION untouched so generation-metric deltas are attributable
to retrieval, not prompt drift.
"""
from dataclasses import dataclass
from typing import Any, Optional

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
    """Assemble (system, user) prompts. Context beyond MAX_CONTEXT_CHARS is
    silently truncated from the tail."""
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


async def generate_and_judge(
    question: str,
    combined_context: Optional[str],
    gen_llm: Any,
    judge_llm: Any,
) -> GenerationResult:
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
