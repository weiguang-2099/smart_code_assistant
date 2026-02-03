import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Smart Code Assistant API"


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "database" in data
