import pytest

from isg_api.security import (
    generate_session_secrets,
    hash_password,
    normalize_username,
    parse_session_cookie,
    secret_matches,
    verify_password,
)


def test_argon2id_password_hash_round_trip_and_wrong_password() -> None:
    password_hash = hash_password("uzun-ve-guvenli-deneme-parolasi")

    assert password_hash.startswith("$argon2id$")
    assert "uzun-ve-guvenli-deneme-parolasi" not in password_hash
    assert verify_password("uzun-ve-guvenli-deneme-parolasi", password_hash)[0]
    assert not verify_password("yanlis-parola", password_hash)[0]


@pytest.mark.parametrize("password", ["kisa", " " * 12, "x" * 129])
def test_new_password_policy_rejects_unsafe_lengths(password: str) -> None:
    with pytest.raises(ValueError):
        hash_password(password)


def test_username_is_normalized_and_strictly_validated() -> None:
    assert normalize_username("  Emin.Bozkurt  ") == "emin.bozkurt"

    with pytest.raises(ValueError):
        normalize_username("iki kelime")


def test_session_cookie_contains_only_public_id_and_random_verifier() -> None:
    secrets = generate_session_secrets()
    parsed = parse_session_cookie(secrets.cookie_value)

    assert parsed == (secrets.session_id, secrets.verifier)
    assert secrets.verifier not in secrets.verifier_hash
    assert secrets.csrf_token not in secrets.csrf_hash
    assert secret_matches(secrets.verifier, secrets.verifier_hash)
    assert secret_matches(secrets.csrf_token, secrets.csrf_hash)
    assert not secret_matches("A" * 43, secrets.verifier_hash)


@pytest.mark.parametrize(
    "value",
    [None, "", "not-a-uuid.token", "00000000-0000-0000-0000-000000000000.short"],
)
def test_malformed_session_cookie_is_rejected(value: str | None) -> None:
    assert parse_session_cookie(value) is None
