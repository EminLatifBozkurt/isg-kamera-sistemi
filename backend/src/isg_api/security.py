"""Parola, oturum doğrulayıcısı ve CSRF belirteci için güvenlik yardımcıları."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass

from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError

PASSWORD_HASH = PasswordHash.recommended()
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
VERIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")

# Olmayan kullanıcıda da gerçek Argon2 işi yaparak kullanıcı adı zamanlama farkını
# küçültürüz. Bu bilinen deneme parolasının özeti, gerçek bir hesaba ait değildir.
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$ilox7iwz1bLXSy10bFaO9w$"
    "9GU9AEN2+QnFN7gf+BhkBSpvCTHfa23xVn+n+zccyGU"
)


@dataclass(frozen=True, slots=True)
class SessionSecrets:
    session_id: uuid.UUID
    verifier: str
    csrf_token: str

    @property
    def cookie_value(self) -> str:
        return f"{self.session_id}.{self.verifier}"

    @property
    def verifier_hash(self) -> str:
        return hash_random_secret(self.verifier)

    @property
    def csrf_hash(self) -> str:
        return hash_random_secret(self.csrf_token)


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Kullanıcı adı 3–64 karakter olmalı; küçük harf, rakam, nokta, "
            "alt çizgi ve kısa çizgi içerebilir"
        )
    return normalized


def validate_new_password(password: str) -> None:
    """Uzun parolalara izin verir; zorunlu yapay karakter bileşimi uygulamaz."""
    if len(password) < 12:
        raise ValueError("Parola en az 12 karakter olmalıdır")
    if len(password) > 128:
        raise ValueError("Parola en fazla 128 karakter olmalıdır")
    if password.isspace():
        raise ValueError("Parola yalnız boşluklardan oluşamaz")


def hash_password(password: str) -> str:
    validate_new_password(password)
    return PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    """Doğrular; ayarlar eskidiyse yeni özeti ikinci değer olarak döndürür."""
    try:
        return PASSWORD_HASH.verify_and_update(password, password_hash)
    except (PwdlibError, ValueError):
        # Bozuk/unsupported bir özet giriş işlemini 500'e dönüştürmemelidir.
        return False, None


def generate_session_secrets() -> SessionSecrets:
    # token_urlsafe(32) her belirteç için 256 bit CSPRNG girdisi kullanır.
    return SessionSecrets(
        session_id=uuid.uuid4(),
        verifier=secrets.token_urlsafe(32),
        csrf_token=secrets.token_urlsafe(32),
    )


def parse_session_cookie(value: str | None) -> tuple[uuid.UUID, str] | None:
    if value is None or len(value) > 100:
        return None
    identifier, separator, verifier = value.partition(".")
    if not separator or not VERIFIER_PATTERN.fullmatch(verifier):
        return None
    try:
        session_id = uuid.UUID(identifier)
    except ValueError:
        return None
    return session_id, verifier


def hash_random_secret(secret: str) -> str:
    """Yüksek entropili rastgele belirteç için hızlı tek yönlü doğrulayıcı."""
    return hashlib.sha256(secret.encode("ascii")).hexdigest()


def secret_matches(secret: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_random_secret(secret), expected_hash)
