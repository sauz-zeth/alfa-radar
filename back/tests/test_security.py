from back.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("secret123")
    assert password_hash != "secret123"
    assert verify_password("secret123", password_hash)
    assert not verify_password("wrong", password_hash)


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-id")
    assert decode_access_token(token) == "user-id"
