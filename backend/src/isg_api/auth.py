"""Sunucuda tutulan oturum, HttpOnly cookie ve CSRF korumalı giriş akışı."""

from __future__ import annotations

import hmac
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from isg_api.config import Settings
from isg_api.database import get_database_session
from isg_api.models import AppUser, UserRole, UserSession
from isg_api.security import (
    DUMMY_PASSWORD_HASH,
    generate_session_secrets,
    normalize_username,
    parse_session_cookie,
    secret_matches,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Oturum"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: SecretStr


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    role: UserRole


class AuthResponse(BaseModel):
    user: UserResponse


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: AppUser
    session: UserSession


DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def cookie_names(settings: Settings) -> tuple[str, str]:
    # __Host- öneki yalnız Secure cookie ile geçerlidir; yerel HTTP geliştirmede
    # kısa ve genel adlar kullanılır.
    if settings.session_cookie_secure:
        return "__Host-id", "__Host-csrf"
    return "id", "csrf"


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Oturum geçersiz veya süresi dolmuş",
        headers={"WWW-Authenticate": "Cookie"},
    )


def login_error() -> HTTPException:
    # Kullanıcının varlığı, pasifliği veya kilit durumu ayrı ayrı açıklanmaz.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kullanıcı adı veya parola hatalı",
    )


def require_same_origin_login(request: Request) -> None:
    """Tarayıcıdaki login-CSRF girişimini Origin başlığıyla reddeder."""
    origin = request.headers.get("Origin")
    if origin is None:
        # Komut satırı istemcilerinde Origin bulunmayabilir; tarayıcı cross-site
        # POST istekleri bu başlığı gönderir.
        return
    expected_origin = str(request.base_url).rstrip("/")
    if not hmac.compare_digest(origin.rstrip("/"), expected_origin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="İstek kaynağı doğrulanamadı",
        )


def authenticate_user(
    database: Session,
    *,
    username: str,
    password: str,
    settings: Settings,
    now: datetime,
) -> AppUser | None:
    try:
        normalized = normalize_username(username)
    except ValueError:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None

    user = database.scalar(select(AppUser).where(AppUser.username == normalized))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None

    verified, updated_hash = verify_password(password, user.password_hash)
    locked = user.locked_until is not None and user.locked_until > now
    if not verified or locked or not user.is_active:
        if not verified and not locked and user.is_active:
            user.failed_login_count += 1
            if user.failed_login_count >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
        database.commit()
        return None

    if updated_hash is not None:
        user.password_hash = updated_hash
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    database.commit()
    return user


def create_server_session(
    database: Session, *, user: AppUser, settings: Settings, now: datetime
) -> tuple[UserSession, str, str]:
    secrets = generate_session_secrets()
    absolute_expiry = now + timedelta(hours=settings.session_absolute_hours)
    idle_expiry = min(
        absolute_expiry,
        now + timedelta(minutes=settings.session_idle_minutes),
    )
    server_session = UserSession(
        id=secrets.session_id,
        user_id=user.id,
        verifier_hash=secrets.verifier_hash,
        csrf_hash=secrets.csrf_hash,
        created_at=now,
        expires_at=absolute_expiry,
        idle_expires_at=idle_expiry,
        last_seen_at=now,
    )
    database.add(server_session)
    database.commit()
    return server_session, secrets.cookie_value, secrets.csrf_token


def set_auth_cookies(
    response: Response,
    *,
    session_cookie: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    session_name, csrf_name = cookie_names(settings)
    max_age = settings.session_absolute_hours * 60 * 60
    common = {
        "max_age": max_age,
        "secure": settings.session_cookie_secure,
        "samesite": "strict",
        "path": "/",
    }
    response.set_cookie(session_name, session_cookie, httponly=True, **common)
    response.set_cookie(csrf_name, csrf_token, httponly=False, **common)
    response.headers["Cache-Control"] = "no-store"


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    session_name, csrf_name = cookie_names(settings)
    response.delete_cookie(
        session_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        csrf_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"


def get_current_authentication(
    request: Request,
    database: DatabaseSession,
) -> AuthenticatedSession:
    settings = get_settings(request)
    session_name, _csrf_name = cookie_names(settings)
    parsed = parse_session_cookie(request.cookies.get(session_name))
    if parsed is None:
        raise authentication_error()
    session_id, verifier = parsed

    server_session = database.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user))
        .where(UserSession.id == session_id)
    )
    if server_session is None or not secret_matches(verifier, server_session.verifier_hash):
        raise authentication_error()

    now = datetime.now(UTC)
    expired = now >= server_session.expires_at or now >= server_session.idle_expires_at
    if server_session.revoked_at is not None or expired or not server_session.user.is_active:
        if server_session.revoked_at is None:
            server_session.revoked_at = now
            database.commit()
        raise authentication_error()

    server_session.last_seen_at = now
    server_session.idle_expires_at = min(
        server_session.expires_at,
        now + timedelta(minutes=settings.session_idle_minutes),
    )
    database.commit()
    return AuthenticatedSession(user=server_session.user, session=server_session)


CurrentAuthentication = Annotated[AuthenticatedSession, Depends(get_current_authentication)]


def require_csrf(
    request: Request,
    authentication: CurrentAuthentication,
) -> AuthenticatedSession:
    settings = get_settings(request)
    _session_name, csrf_name = cookie_names(settings)
    cookie_token = request.cookies.get(csrf_name)
    header_token = request.headers.get("X-CSRF-Token")
    if (
        cookie_token is None
        or header_token is None
        or not hmac.compare_digest(cookie_token, header_token)
        or not secret_matches(header_token, authentication.session.csrf_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF doğrulaması başarısız",
        )
    return authentication


def require_roles(*roles: UserRole):
    allowed = set(roles)

    def role_dependency(authentication: CurrentAuthentication) -> AuthenticatedSession:
        if authentication.user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için yetkiniz yok",
            )
        return authentication

    return role_dependency


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    database: DatabaseSession,
) -> AuthResponse:
    settings = get_settings(request)
    require_same_origin_login(request)
    user = authenticate_user(
        database,
        username=payload.username,
        password=payload.password.get_secret_value(),
        settings=settings,
        now=datetime.now(UTC),
    )
    if user is None:
        raise login_error()

    _server_session, cookie_value, csrf_token = create_server_session(
        database,
        user=user,
        settings=settings,
        now=datetime.now(UTC),
    )
    set_auth_cookies(
        response,
        session_cookie=cookie_value,
        csrf_token=csrf_token,
        settings=settings,
    )
    return AuthResponse(user=UserResponse.model_validate(user))


@router.get("/me", response_model=AuthResponse)
def me(response: Response, authentication: CurrentAuthentication) -> AuthResponse:
    response.headers["Cache-Control"] = "no-store"
    return AuthResponse(user=UserResponse.model_validate(authentication.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    database: DatabaseSession,
    authentication: Annotated[AuthenticatedSession, Depends(require_csrf)],
) -> None:
    authentication.session.revoked_at = datetime.now(UTC)
    database.commit()
    clear_auth_cookies(response, get_settings(request))
