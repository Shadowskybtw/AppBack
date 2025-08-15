import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_get_stocks_unauthorized():
    """Test getting stocks without valid user."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/stocks/999999")
        # Should create user automatically
        assert response.status_code == 200
        data = response.json()
        assert "stocks" in data
        assert "total" in data
        assert "completed" in data
        assert "available" in data


@pytest.mark.asyncio
async def test_register_user():
    """Test user registration."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "tg_id": 123456789,
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
            "username": "testuser"
        }
        response = await ac.post("/api/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["user"]["tg_id"] == 123456789
        assert data["user"]["first_name"] == "Test"


@pytest.mark.asyncio
async def test_register_user_invalid_phone():
    """Test user registration with invalid phone."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        payload = {
            "tg_id": 123456789,
            "first_name": "Test",
            "last_name": "User",
            "phone": "invalid-phone",
            "username": "testuser"
        }
        response = await ac.post("/api/register", json=payload)
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_profile_unregistered():
    """Test getting profile for unregistered user."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/main/999999999")
        assert response.status_code == 200
        data = response.json()
        assert data["registered"] is False
        assert data["completedStocks"] == 0


@pytest.mark.asyncio
async def test_redeem_unauthorized():
    """Test redeem endpoint without admin privileges."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/redeem/123456789")
        assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_send_webapp_button_no_token():
    """Test sending webapp button without bot token."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/send_webapp_button/123456789")
        assert response.status_code == 500  # Internal server error
