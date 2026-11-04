# TEST/back/test_security.py
from app.security.hashing import hash_password, verify_password
from app.security.jwt import create_access_token, decode_access_token


def test_hash_and_verify() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("otra", hashed)
    assert not verify_password("secret123", "no-es-un-hash")


def test_jwt_roundtrip() -> None:
    payload = decode_access_token(create_access_token(7, "infra"))
    assert payload is not None
    assert payload["sub"] == "7"
    assert payload["role"] == "infra"


def test_jwt_expired_or_tampered() -> None:
    assert decode_access_token(create_access_token(1, "admin", expires_minutes=-1)) is None
    assert decode_access_token(create_access_token(1, "admin") + "x") is None
