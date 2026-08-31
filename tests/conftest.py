import pytest
from httpx import AsyncClient, ASGITransport
from vantage.api.app import app


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
