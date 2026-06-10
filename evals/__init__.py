"""Evaluation harness for Smart Code Assistant's GraphRAG retrieval.

This package imports ``app.services.code_graph.*`` from ``backend-fastapi/`` and
needs that directory on sys.path before any submodule loads it. The path
manipulation is done here in __init__ so every entry into the package (CLI,
tests, library import) sees the same path setup.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_PATH = _REPO_ROOT / "backend-fastapi"
if str(_BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(_BACKEND_PATH))
