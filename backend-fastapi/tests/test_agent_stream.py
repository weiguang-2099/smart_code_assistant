"""Tests for streaming agent endpoints"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core.deps import get_current_user
from app.models.user import User


@pytest.fixture
def mock_user():
    return User(id=1, username="test", email="test@test.com", hashed_password="x")


@pytest.fixture
def client(mock_user):
    """
    TestClient with the auth dependency overridden.

    FastAPI resolves dependencies via the dependency_overrides registry, not by
    function-level patching, so unittest.mock.patch on get_current_user has no
    effect here — we must register the override on the app itself.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


class TestAgentStream:
    """Test streaming chat endpoint"""

    def test_stream_endpoint_exists(self, client):
        """Stream endpoint should be accessible (not 404)."""
        response = client.post(
            "/api/v1/agent/chat/stream",
            json={"message": "hello", "history": [], "language": "python"},
        )
        assert response.status_code != 404

    def test_stream_returns_sse_format(self, client):
        """Should return Server-Sent Events format with content + [DONE] sentinel."""
        mock_chunks = ["Hello", " world", "!"]

        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk

        with patch(
            "app.services.langchain_glm_service.langchain_glm_service.stream_chat",
            mock_stream,
        ):
            response = client.post(
                "/api/v1/agent/chat/stream",
                json={"message": "hello", "history": [], "language": "python"},
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            content = response.text
            assert "data:" in content
            # Implementation emits a typed 'done' SSE event rather than the
            # OpenAI-style '[DONE]' text sentinel.
            assert "event: done" in content
            for chunk in mock_chunks:
                assert chunk in content
