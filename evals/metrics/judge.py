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
