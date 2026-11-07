from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.maintenance import purge_expired_auth_material
from app.db.base import Base
from app.models import AuthSession, AuthToken, PhoneOtpChallenge, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_user(db: Session) -> User:
    user = User(
        email="security@example.com",
        email_normalized="security@example.com",
        full_name="Security Test",
    )
    db.add(user)
    db.flush()
    return user


def test_auth_token_hash_is_unique(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add_all(
        [
            AuthToken(
                user_id=user.id,
                token_hash="a" * 64,
                purpose="verify_email",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
            AuthToken(
                user_id=user.id,
                token_hash="a" * 64,
                purpose="password_reset",
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_auth_token_rejects_unknown_purpose(db_session: Session) -> None:
    user = make_user(db_session)
    db_session.add(
        AuthToken(
            user_id=user.id,
            token_hash="b" * 64,
            purpose="login",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_cleanup_clears_expired_otp_ciphertext_and_old_tokens(db_session: Session) -> None:
    user = make_user(db_session)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            PhoneOtpChallenge(
                user_id=user.id,
                phone_e164="+265991234567",
                purpose="login",
                code_hash="c" * 64,
                code_ciphertext="encrypted-otp",
                expires_at=now - timedelta(hours=1),
                delivery_status="delivered",
            ),
            AuthToken(
                user_id=user.id,
                token_hash="d" * 64,
                purpose="verify_email",
                expires_at=now - timedelta(days=8),
            ),
            AuthSession(
                user_id=user.id,
                refresh_token_hash="e" * 64,
                expires_at=now - timedelta(days=91),
            ),
        ]
    )
    db_session.commit()

    result = purge_expired_auth_material(db_session)

    challenge = db_session.scalar(select(PhoneOtpChallenge))
    assert challenge is not None
    assert challenge.code_ciphertext is None
    assert db_session.scalar(select(AuthToken)) is None
    assert db_session.scalar(select(AuthSession)) is None
    assert result["otp_ciphertexts_cleared"] == 1
