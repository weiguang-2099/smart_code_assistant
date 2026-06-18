"""
Shared pytest fixtures and test configuration.

Provides isolated environment, mock clients, and helper utilities so unit tests
never touch real MySQL / Neo4j / ChromaDB / Zhipu services.
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest


# Ensure backend-fastapi/ is on sys.path so `import app` works under any CWD.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
async def _clear_retrieval_cache():
    """Clear the in-memory retrieval cache before every test to prevent cache pollution."""
    from app.core.cache import global_cache_manager
    await global_cache_manager.clear()
    yield
    await global_cache_manager.clear()


@pytest.fixture(autouse=True)
def _isolated_test_env(monkeypatch):
    """
    Provide deterministic environment for every test - no real secrets, no real services.
    The autouse fixture runs before any application import that reads settings.
    """
    monkeypatch.setenv("FASTAPI_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only-do-not-use-in-prod")
    monkeypatch.setenv("ZHIPUAI_API_KEY", "test-zhipu-key")
    monkeypatch.setenv("DATALAB_API_KEY", "test-datalab-key")
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-neo4j-password")
    # DATABASE_URL intentionally left untouched - app.database creates a lazy
    # async engine that never connects unless a session is actually awaited.


@pytest.fixture
def mock_neo4j_client():
    """Mock async Neo4j client with the methods the codebase actually uses."""
    client = MagicMock()
    client.execute_query = AsyncMock(return_value=[])
    client.batch_get_entity_context = AsyncMock(return_value=[])
    client.get_dependencies = AsyncMock(return_value=[])
    client.get_impact_analysis = AsyncMock(return_value=[])
    client.find_path = AsyncMock(return_value=[])
    client.create_function = AsyncMock(return_value=None)
    client.create_class = AsyncMock(return_value=None)
    client.create_import = AsyncMock(return_value=None)
    client.create_relationship = AsyncMock(return_value=None)
    client.close = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_chromadb_client():
    """Mock synchronous ChromaDB client (the wrapper runs in to_thread)."""
    client = MagicMock()
    client.search_all = MagicMock(return_value={"functions": [], "classes": []})
    client.add_entities = MagicMock(return_value=None)
    client.delete_by_project = MagicMock(return_value=None)
    return client


@pytest.fixture
def sample_python_code():
    """Small, parseable Python source used across analyzer / graph tests."""
    return (
        "import os\n"
        "from typing import List\n\n"
        "class Calculator:\n"
        "    def add(self, a: int, b: int) -> int:\n"
        "        return a + b\n\n"
        "def greet(name: str) -> str:\n"
        "    if name:\n"
        "        return f'Hello {name}'\n"
        "    return 'Hello'\n"
    )


@pytest.fixture
def smelly_python_code():
    """Source intentionally containing patterns the smell-detector should flag."""
    return (
        "def process(data):\n"
        "    " + "\n    ".join([f"x{i} = {i}" for i in range(120)]) + "\n"
        "    return x0\n"
    )
