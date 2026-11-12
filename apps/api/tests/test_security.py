import uuid

import jwt

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decrypt_otp,
    encrypt_otp,
    hash_otp,
    hash_refresh_token,
    new_otp,
    new_refresh_token,
    verify_password,
)


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    from app.core.security import hash_password

    encoded = hash_password("a-long-and-unique-password")
    assert encoded != "a-long-and-unique-password"
    assert verify_password("a-long-and-unique-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_refresh_token_is_random_and_only_hash_is_stored() -> None:
    first = new_refresh_token()
    second = new_refresh_token()
    assert first != second
    assert len(first) >= 64
    assert hash_refresh_token(first) != first
    assert len(hash_refresh_token(first)) == 64


def test_otp_hash_is_stable_and_bound_to_phone() -> None:
    code = "012345"
    expected = hash_otp("+265991234567", code)
    assert hash_otp("+265991234567", code) == expected
    assert hash_otp("+265881234567", code) != expected
    assert hash_otp("+265991234567", "012346") != expected


def test_otp_encryption_round_trip() -> None:
    code = new_otp()
    encrypted = encrypt_otp(code)
    assert encrypted != code
    assert decrypt_otp(encrypted) == code


def test_access_token_contains_session_binding() -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4())
    assert isinstance(token, str)
    assert token.count(".") == 2
    payload = jwt.decode(
        token,
        get_settings().jwt_secret_key,
        algorithms=[get_settings().jwt_algorithm],
        issuer=get_settings().jwt_issuer,
        audience=get_settings().jwt_audience,
    )
    assert payload["sid"]
    assert payload["jti"]


def test_refresh_token_is_not_exposed_in_api_token_schema() -> None:
    from app.modules.identity.schemas import TokenResponse

    assert "refresh_token" not in TokenResponse.model_fields
