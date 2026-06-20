"""Integration test (real Neo4j) for ``create_call_relationship``.

Regression: a module-level function (``class_name`` = NULL) must still receive
its CALLS edges. The original Cypher matched the caller with
``{name, module_path, class_name: $caller_class}``; in Cypher a property map
holding a null value matches nothing, so every module-level caller
(``register``, ``login``, ...) silently got zero CALLS edges while methods
worked. Surfaced by the eval harness (graph_neighbor_recall floor).

Hits a real Neo4j (the docker-compose service); skipped automatically when the
database is unreachable, so the mock-only unit suite / CI without services stays
green.
"""
import os
import uuid

import pytest

from app.services.code_graph.config import CodeGraphConfig
from app.services.code_graph.neo4j_client import Neo4jClient


async def _connect_or_skip() -> Neo4jClient:
    # Explicit config so the autouse fake-credentials fixture cannot point us at
    # a non-existent instance; falls back to the compose defaults.
    cfg = CodeGraphConfig()
    cfg.neo4j_uri = os.getenv("NEO4J_TEST_URI", "bolt://localhost:7687")
    cfg.neo4j_user = os.getenv("NEO4J_TEST_USER", "neo4j")
    cfg.neo4j_password = os.getenv("NEO4J_TEST_PASSWORD", "codegraph123")
    client = Neo4jClient(config=cfg)
    try:
        await client.connect()
    except Exception as exc:  # ServiceUnavailable / AuthError / driver errors
        pytest.skip(f"Neo4j not reachable for integration test: {exc}")
    return client


@pytest.mark.asyncio
async def test_module_level_caller_gets_calls_edge():
    client = await _connect_or_skip()
    tag = uuid.uuid4().hex[:8]
    mod = f"test/_pytest_calls_{tag}.py"
    caller, callee = f"caller_{tag}", f"callee_{tag}"
    try:
        # Two module-level functions: class_name absent (== NULL), exactly how the
        # extractor stores top-level defs such as register / get_password_hash.
        await client.execute_query(
            "CREATE (:Function {name:$caller, module_path:$m}),"
            " (:Function {name:$callee, module_path:$m})",
            {"caller": caller, "callee": callee, "m": mod},
        )
        await client.create_call_relationship(
            caller_module=mod,
            caller_function=caller,
            caller_class=None,
            callee_function=callee,
        )
        rows = await client.execute_query(
            "MATCH (a:Function {name:$caller, module_path:$m})"
            "-[:CALLS]->(b:Function {name:$callee, module_path:$m})"
            " RETURN count(*) AS c",
            {"caller": caller, "callee": callee, "m": mod},
        )
        assert rows[0]["c"] == 1, "module-level caller should get a CALLS edge"
    finally:
        await client.execute_query(
            "MATCH (n:Function {module_path:$m}) DETACH DELETE n", {"m": mod}
        )
        await client.close()
