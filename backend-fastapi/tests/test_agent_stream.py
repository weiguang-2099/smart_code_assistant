"""Tests for streaming agent endpoints"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from app.main import app


class TestAgentStream:
    """Test streaming chat endpoint"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_auth(self):
        """Mock authenticated user"""
        from app.models.user import User
        return User(id=1, username="test", email="test@test.com", hashed_password="x")

    def test_stream_endpoint_exists(self, client, mock_auth):
        """Stream endpoint should be accessible"""
        with patch('app.core.deps.get_current_user', return_value=mock_auth):
            response = client.post(
                "/api/v1/agent/chat/stream",
                json={"message": "hello", "history": [], "language": "python"},
                headers={"Authorization": "Bearer test-token"}
            )
            # Should not return 404
            assert response.status_code != 404

    def test_stream_returns_sse_format(self, client, mock_auth):
        """Should return Server-Sent Events format"""
        mock_chunks = ["Hello", " world", "!"]

        async def mock_stream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk

        with patch('app.core.deps.get_current_user', return_value=mock_auth):
            with patch('app.services.langchain_glm_service.langchain_glm_service.stream_chat', mock_stream):
                response = client.post(
                    "/api/v1/agent/chat/stream",
                    json={"message": "hello", "history": [], "language": "python"},
                    headers={"Authorization": "Bearer test-token"}
                )

                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")

                # Check SSE format
                content = response.text
                assert "data:" in content
                assert "[DONE]" in content
