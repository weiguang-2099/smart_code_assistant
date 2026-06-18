# Smart Code Assistant — Phase 1b: Generation Evals + LLM Provider Abstraction

Date: 2026-06-11
Status: Approved (brainstorming -> ready for implementation plan)
Scope: Stage 1 of Approach A. Stage 2 (real LangGraph agent rewrite + trajectory
metrics) is a separate spec, written after this stage ships.
Builds on: `2026-06-10-evals-harness-design.md` (v1, retrieval metrics — shipped)

## 1. Goal

Extend the shipped retrieval-only eval harness so the README can show
generation-quality numbers, and make the backend LLM layer provider-agnostic
(ZhipuAI / OpenAI switchable via environment).

Deliverables:

1. **LLM provider abstraction** — backend switches between ZhipuAI and OpenAI
   via env config; default remains GLM; zero call-site changes.
2. **Real-codebase golden set** — `evals/golden_set/backend_fastapi.jsonl`,
   30-50 cases over `backend-fastapi/app/`, using the v1 authoring workflow
   (AI drafts ~50 candidates, human reviews and trims).
3. **Generation evaluation** — minimal RAG chain inside evals (retrieved
   context + question -> fixed prompt -> LLM answer), judged by GLM-4-plus on
   `faithfulness` and `answer_relevance` (reference-free metrics).
4. **README "Evaluation" section** — baseline results tables (retrieval +
   generation) annotated with git SHA, date, and models used.

## 2. Non-goals (deferred to Stage 2 or later)

- LangGraph agent rewrite of `/api/v1/agent/chat` (Stage 2)
- Agent trajectory metrics: tool-call correctness, step count, loop/stall
  detection, task_success (Stage 2 — meaningless against the current
  keyword-rule dispatcher)
- `correctness` judge metric (requires reference answers; authoring deferred)
- Running generation evals in CI (costs API money; CI keeps the free
  retrieval-only smoke)
- Model routing / cost-aware tiering (checklist Phase 3)
- RAGAS or other eval-framework dependencies

## 3. Context: why trajectory metrics moved to Stage 2

Investigation findings (2026-06-11):

- `langgraph` is in `requirements.txt` but never imported anywhere in
  `backend-fastapi/app/`. The README's "LangGraph agent orchestration" claim
  is currently not backed by code.
- `/api/v1/agent/chat` (`agent.py:435-482`) selects tools by keyword matching
  on the user message (e.g. "security" triggers the security tool), not by LLM
  decision. Semantic search only fires on explicit search keywords and
  hardcodes `project_id=1`.
- Consequence: golden-set questions would trigger near-zero retrieval through
  that endpoint, and "trajectory" would measure keyword rules, not agent
  behavior.

Decision: evaluate a controlled RAG chain now (this spec); rewrite the agent
for real (LangGraph `create_react_agent` with GraphRAG retrieval, callers/
callees, and analysis tools) and evaluate its trajectory in Stage 2.

## 4. Decisions locked during brainstorming

| Decision | Choice |
|---|---|
| OpenAI support scope | Backend-wide provider config (env switch), not judge-only |
| Judge model | GLM-4-plus by default (`quality` tier); overridable to any provider model |
| Answer generator under evaluation | Minimal RAG chain inside evals (Stage 1); real agent endpoint in Stage 2 |
| Reference answers | None — only reference-free judge metrics (faithfulness, answer_relevance) |
| Trajectory metrics | Full trajectory eval incl. task_success — deferred to Stage 2 with the agent rewrite |
| Generation evals in CI | No — opt-in local flag only; CI smoke stays retrieval-only |
| New dependencies | None — judge calls go through the existing `langchain-openai` stack |

## 5. Provider abstraction design

All changes live in `backend-fastapi/app/core/config.py` and
`backend-fastapi/app/services/langchain_glm_service.py`. Call sites do not
change.

### 5.1 New settings (all defaulted, backward compatible)

| Variable | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `zhipuai` | `zhipuai` or `openai` |
| `LLM_API_KEY` | `""` | Falls back to `ZHIPUAI_API_KEY` when empty (existing `.env` files keep working) |
| `LLM_BASE_URL` | `""` | When empty, resolved from provider preset |
| `LLM_MODEL` | `""` | `default` tier override |
| `LLM_MODEL_FAST` | `""` | `fast` tier override |
| `LLM_MODEL_QUALITY` | `""` | `quality` tier override |
| `LLM_MODEL_LIGHT` | `""` | `light` tier override |

### 5.2 Provider presets

| Tier | zhipuai | openai |
|---|---|---|
| base_url | `https://open.bigmodel.cn/api/paas/v4/` | `https://api.openai.com/v1` |
| default | `glm-4` | `gpt-4o` |
| fast | `glm-4-flash` | `gpt-4o-mini` |
| quality | `glm-4-plus` | `gpt-4o` |
| light | `glm-4-air` | `gpt-4o-mini` |

### 5.3 Implementation shape

- `LangChainGLMService` is renamed to `LLMService`;
  `LangChainGLMService = LLMService` stays as an alias.
- Constructor gains `tier: str = "default"`. Explicit `model=` / `base_url=` /
  `api_key=` arguments still win over tier resolution (constructor precedence:
  explicit arg > env override > provider preset).
- The four module-level singletons keep their names
  (`langchain_glm_service`, `glm_service_flash`, `glm_service_plus`,
  `glm_service_air`) and map to tiers `default` / `fast` / `quality` / `light`.
- **Lazy initialization fix**: today the singletons construct `ChatOpenAI` at
  import time and raise if no API key is configured, which prevents the app
  from even starting. The new implementation defers LLM construction to first
  use (`self._llm = None`, built on first access via a property). Missing key
  raises at first call, with a clear message naming both `LLM_API_KEY` and
  `ZHIPUAI_API_KEY`.
- Underlying client remains `ChatOpenAI` for both providers (ZhipuAI exposes
  an OpenAI-compatible API) — this is the deliberate design point: one
  protocol, N providers.

### 5.4 Backend tests

In `backend-fastapi/tests/` (pure unit, no network):

- Preset resolution per provider and tier
- Env override beats preset; explicit constructor arg beats env
- `LLM_API_KEY` empty falls back to `ZHIPUAI_API_KEY`
- Import with no keys configured does not raise; first call does
- `LangChainGLMService` alias still constructs

## 6. Golden set: `backend_fastapi.jsonl`

Workflow, schema, matching policy, and validation are unchanged from v1 spec
sections 6 (see `2026-06-10-evals-harness-design.md`). Summary of what is
executed now:

1. Claude scans `backend-fastapi/app/` and drafts ~50 candidates to
   `evals/golden_set/backend_fastapi.draft.jsonl` using the v1 category
   distribution (definition_lookup 12, feature_lookup 12, dependency_trace 10,
   impact_analysis 8, cross_file_flow 8).
2. Every candidate's `expected_files` is verified against the working tree;
   `expected_graph_neighbors` use simple unqualified names (v1 TBD #3).
3. Human reviews, trims to 30-50 keepers, saves as
   `evals/golden_set/backend_fastapi.jsonl`.
4. `validate.py` must pass on the final file.

No `reference_answer` field is added (locked decision: reference-free metrics
only).

## 7. Generation evaluation design

### 7.1 Data flow

```
golden case ──► CodeGraphRetriever.retrieve()        (existing, unchanged)
                      │
                      ├──► retrieval metrics          (existing, unchanged)
                      │
                      └──► [--with-generation only]
                           generation.py: context + question
                                 │   fixed RAG prompt -> LLM answer
                                 │
                                 ├──► judge: faithfulness      (context + answer -> 1-5)
                                 └──► judge: answer_relevance  (question + answer -> 1-5)
```

Retrieval runs once per case; its output feeds both metric families.

### 7.2 New modules

- `evals/generation.py` — the RAG chain. The prompt template is a versioned
  constant in the module (`GEN_PROMPT_VERSION = "v1"`), recorded in result
  meta. Phase 2 retrieval changes must not change this prompt, so generation
  deltas are attributable to retrieval. Generator model defaults to the
  provider `default` tier; `--gen-model` overrides.
- `evals/metrics/judge.py` — two judge metrics. Judge model defaults to the
  `quality` tier (GLM-4-plus); `--judge-model` overrides. `temperature=0`.
  Judge returns strict JSON `{"score": <int 1-5>, "reasoning": "<str>"}`.
  Parse failure triggers exactly one retry with a "return only JSON" reminder
  appended; second failure records `null` and increments `judge_parse_error`.

### 7.3 Metric definitions

| Metric | Judge sees | Question asked | Blind to |
|---|---|---|---|
| `faithfulness` (1-5) | retrieved context + answer | Is every technical claim in the answer supported by the context? 5 = fully grounded, 1 = largely fabricated | the question (prevents "relevant therefore faithful" bias) |
| `answer_relevance` (1-5) | question + answer | Does the answer directly address the question? | the retrieved context |

Aggregation:

- Arithmetic mean per metric, overall and per category (consistent with v1
  macro averaging).
- Additionally report `pct_score_ge_4` (share of cases scoring >= 4) — the
  human-readable headline ("85% of answers are faithful to the retrieved
  code").
- Cases with `null` scores are excluded from means; sample size is shown next
  to each aggregate, v1-style.

### 7.4 CLI additions

Default behavior without new flags is byte-identical to v1 (free, no LLM
calls).

```
--with-generation        enable generation + judge (requires LLM_API_KEY or ZHIPUAI_API_KEY)
--gen-model NAME         override generator model
--judge-model NAME       override judge model
--gen-timeout INT        per-case generation+judge budget in seconds (default 120)
```

Concurrency reuses the existing `--concurrency` semaphore; the per-case
generation budget is enforced with `asyncio.wait_for` around the
gen+judge sequence, separate from the 30s retrieval timeout.

### 7.5 Result JSON additions

Per case:

```json
"generation": {
  "answer": "<full generated answer>",
  "faithfulness": 4,
  "faithfulness_reasoning": "<judge reasoning>",
  "answer_relevance": 5,
  "answer_relevance_reasoning": "<judge reasoning>",
  "error": null
}
```

`meta.config` gains `gen_model`, `judge_model`, `gen_prompt_version`,
`with_generation: true`. Aggregate gains a `generation` block with means,
`pct_score_ge_4`, `n`, `gen_error_rate`, and `judge_parse_error` count.
Reporter prints one extra table section when generation data is present.

### 7.6 Cost envelope

40 cases x (1 generation + 2 judge calls) = ~120 LLM calls per full run.
At GLM-4 / GLM-4-plus pricing this is on the order of a few RMB per run —
acceptable for local iteration. CI never pays it.

## 8. Error handling

| Failure | Behavior | Exit |
|---|---|---|
| `--with-generation` with no API key configured | clear error before any case runs | 2 |
| Single-case generation or judge API failure | `generation.error` set, scores null, retrieval metrics for the case unaffected, counted in `gen_error_rate`, run continues | 0 |
| Single-case gen+judge timeout (> `--gen-timeout`) | same as above, error = "timeout" | 0 |
| Judge JSON unparseable after one retry | score null, `judge_parse_error` incremented, other metrics keep their values | 0 |

v1 error semantics (exit 2 config errors, exit 3 infra errors, per-case
isolation) are unchanged.

## 9. Testing strategy

Evals tests stay network-free (v1 principle):

- `evals/tests/test_judge.py` — prompt builders and the JSON score parser are
  pure functions: valid JSON, JSON embedded in prose, retry path, hard
  failure. A score outside 1-5 is rejected as a parse error (not clamped), to
  keep the judge contract strict.
- `evals/tests/test_generation.py` — RAG chain with an injected fake LLM
  client: prompt assembly (context truncation order, question placement),
  timeout path, error capture.
- Reporter snapshot test extended with a generation block fixture.
- Provider abstraction tests live in `backend-fastapi/tests/` (section 5.4).

Real-LLM runs are local-only and manual; CI smoke remains retrieval-only.

## 10. README additions

New "Evaluation" section:

- One command to run retrieval-only and one to run with generation
- Baseline results: two tables (retrieval metrics, generation metrics) with
  git SHA, date, golden set size, gen/judge models
- Limitation note: judge and generator are same-family models (GLM); the
  provider abstraction allows re-judging with OpenAI models for cross-checks
- Pointer to `EVAL_PROJECT_ID = 99999` index isolation and how to index the
  corpus locally

The tech-stack table's LangGraph row is corrected to reflect reality until
Stage 2 lands (listed as "planned: agent rewrite" rather than implying a
shipped LangGraph orchestrator).

## 11. Suggested commit order

1. Provider abstraction in `config.py` + `langchain_glm_service.py` + backend
   unit tests (independently shippable)
2. `.env.example` + README config table rows for the new LLM_* variables
3. `evals/metrics/judge.py` + `test_judge.py` (pure functions first)
4. `evals/generation.py` + `test_generation.py`
5. Runner/reporter/CLI wiring for `--with-generation` + reporter test update
6. AI-drafted `backend_fastapi.draft.jsonl` (~50 candidates)
7. Human-reviewed `backend_fastapi.jsonl` (30-50 final) + validate pass
8. Baseline runs (retrieval-only and with generation) + README "Evaluation"
   section with the numbers
9. README tech-stack honesty fix (LangGraph row)

Steps 1-5 require no golden set; steps 6-8 require a locally indexed corpus.

## 12. Stage 2 preview (separate spec, not designed here)

Rewrite `/api/v1/agent/chat` as a real tool-calling agent (LangGraph
`create_react_agent`) whose tools include GraphRAG search, find_callers/
find_callees, and the code-analysis tools; then add trajectory metrics
(expected-tool annotations on golden cases, tool-call correctness, step
count, loop/stall detection, task_success) evaluated end-to-end against the
real agent. The user's locked choices "evaluate the real agent endpoint" and
"full trajectory eval incl. success determination" are fulfilled there.
