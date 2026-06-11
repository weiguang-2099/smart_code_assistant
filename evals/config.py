"""Constants for the evaluation harness. Edit here, not in CLI defaults."""

EVAL_PROJECT_ID = 99999

K_VALUES = (1, 3, 5, 10)

DEFAULT_TOP_K = 10
DEFAULT_MAX_DEPTH = 2
DEFAULT_CONCURRENCY = 5
DEFAULT_PER_CASE_TIMEOUT_S = 30.0
DEFAULT_GEN_TIMEOUT_S = 120.0  # per-case generation + 2 judge calls budget
DEFAULT_OUTPUT_DIR = "evals/results"

CATEGORIES = (
    "definition_lookup",
    "feature_lookup",
    "dependency_trace",
    "impact_analysis",
    "cross_file_flow",
)
