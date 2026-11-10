"""D3 oturum, CSRF ve rol akışını gerçek PostgreSQL + ASGI üzerinde doğrular."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import httpx
from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.main import create_app
from isg_api.models import AppUser, UserRole, UserSession
from isg_api.security import hash_password, parse_session_cookie
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


async def verify_http_flow(
    prefix: str, password: str, settings: Settings
) -> dict[str, Any]:
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    checks: list[str] = []

    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as admin_client:
        media_id = uuid.uuid4()
        response = await admin_client.get(f"/api/v1/media/{media_id}")
        assert response.status_code == 401
        checks.append("unauthorized_media_rejected")

        response = await admin_client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"username": f"{prefix}_admin", "password": password},
        )
        assert response.status_code == 403
        checks.append("cross_origin_login_rejected")

        response = await admin_client.post(
            "/api/v1/auth/login",
            json={"username": f"{prefix}_admin", "password": "bilerek-yanlis-parola"},
        )
        assert response.status_code == 401
        assert "parola" in response.json()["detail"].lower()
        checks.append("wrong_password_rejected")

        response = await admin_client.post(
            "/api/v1/auth/login",
            json={"username": f"{prefix}_admin", "password": password},
        )
        assert response.status_code == 200
        set_cookies = response.headers.get_list("set-cookie")
        session_cookie_header = next(
            item for item in set_cookies if item.startswith("id=")
        )
        csrf_cookie_header = next(
            item for item in set_cookies if item.startswith("csrf=")
        )
        assert "HttpOnly" in session_cookie_header
        assert "SameSite=strict" in session_cookie_header
        assert "HttpOnly" not in csrf_cookie_header
        assert "SameSite=strict" in csrf_cookie_header
        assert "csrf" not in response.json()
        checks.append("secure_cookie_attributes")

        response = await admin_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        assert response.json()["user"]["role"] == "admin"
        checks.append("authenticated_me")

        create_payload = {
            "username": f"{prefix}_created",
            "display_name": "D3 API Kullanıcısı",
            "password": "D3-api-ile-olusturulan-parola",
            "role": "isg",
        }
        response = await admin_client.post("/api/v1/users", json=create_payload)
        assert response.status_code == 403
        checks.append("csrf_missing_rejected")

        csrf_token = admin_client.cookies.get("csrf")
        assert csrf_token is not None
        response = await admin_client.post(
            "/api/v1/users",
            json=create_payload,
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 201
        assert response.json()["role"] == "isg"
        checks.append("admin_create_user")

        cookie_value = admin_client.cookies.get("id")
        parsed = parse_session_cookie(cookie_value)
        assert parsed is not None
        session_id, raw_verifier = parsed

        engine = app.state.database_session_factory.kw["bind"]
        with Session(engine) as database:
            stored_session = database.get(UserSession, session_id)
            assert stored_session is not None
            assert raw_verifier not in stored_session.verifier_hash
            assert csrf_token not in stored_session.csrf_hash
        checks.append("raw_tokens_not_stored")

        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as isg_client:
            response = await isg_client.post(
                "/api/v1/auth/login",
                json={"username": f"{prefix}_isg", "password": password},
            )
            assert response.status_code == 200
            response = await isg_client.get("/api/v1/users")
            assert response.status_code == 403
            response = await isg_client.get(f"/api/v1/media/{media_id}")
            assert response.status_code == 404
        checks.append("isg_role_boundary_and_media_auth")

        response = await admin_client.post("/api/v1/auth/logout")
        assert response.status_code == 403
        response = await admin_client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 204
        response = await admin_client.get("/api/v1/auth/me")
        assert response.status_code == 401
        checks.append("logout_revokes_session")

    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as lock_client:
        for _index in range(settings.login_max_failures):
            response = await lock_client.post(
                "/api/v1/auth/login",
                json={"username": f"{prefix}_lock", "password": "yanlis-parola"},
            )
            assert response.status_code == 401
        response = await lock_client.post(
            "/api/v1/auth/login",
            json={"username": f"{prefix}_lock", "password": password},
        )
        assert response.status_code == 401
        checks.append("temporary_login_lock")

    app.state.database_session_factory.kw["bind"].dispose()
    return {"status": "ok", "checks": checks}


def prepare_users(prefix: str, password: str, settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        with Session(engine) as database:
            for suffix, role in (
                ("admin", UserRole.ADMIN),
                ("isg", UserRole.ISG),
                ("lock", UserRole.ISG),
            ):
                database.add(
                    AppUser(
                        username=f"{prefix}_{suffix}",
                        display_name=f"D3 {suffix}",
                        password_hash=hash_password(password),
                        role=role,
                    )
                )
            database.commit()
    finally:
        engine.dispose()


def cleanup_users(prefix: str, settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        with engine.begin() as connection:
            user_ids = select(AppUser.id).where(AppUser.username.like(f"{prefix}%"))
            connection.execute(
                delete(UserSession).where(UserSession.user_id.in_(user_ids))
            )
            connection.execute(
                delete(AppUser).where(AppUser.username.like(f"{prefix}%"))
            )
    finally:
        engine.dispose()


def main() -> int:
    prefix = f"d3_{uuid.uuid4().hex[:8]}"
    password = "D3-gercek-akis-deneme-parolasi"
    settings = Settings(login_max_failures=3, login_lock_minutes=1)
    prepare_users(prefix, password, settings)
    try:
        result = asyncio.run(verify_http_flow(prefix, password, settings))
    finally:
        cleanup_users(prefix, settings)
        password = ""
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
