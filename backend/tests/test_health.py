import asyncio

import httpx

import isg_api.main as main_module
from isg_api.config import Settings
from isg_api.main import create_app


def test_live_api_does_not_claim_analysis_or_database_is_ready():
    settings = Settings(_env_file=None, app_name="Test İSG", database_password=None)

    async def request_health():
        transport = httpx.ASGITransport(app=create_app(settings))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "service": "Test İSG",
        "version": "0.1.0",
        "status": "ok",
        "analysis": "not_configured",
        "database": "not_configured",
    }


def test_live_api_reports_real_database_state_without_exposing_details(monkeypatch):
    settings = Settings(_env_file=None, database_password="hidden-password")
    monkeypatch.setattr(main_module, "get_database_status", lambda _settings: "ok")

    async def request_health():
        transport = httpx.ASGITransport(app=create_app(settings))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/v1/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert "hidden-password" not in response.text
