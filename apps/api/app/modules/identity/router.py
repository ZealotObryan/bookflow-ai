import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models import AuthSession, User
from app.modules.identity.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)


def _issue_session(db: Session, user: User) -> TokenResponse:
    settings = get_settings()
    refresh = new_refresh_token()
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    db.flush()
    access = create_access_token(user.id, session.id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_minutes * 60,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().jwt_secret_key,
            algorithms=[get_settings().jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "sid"]},
        )
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["sid"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from None

    session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        )
    )
    user = db.get(User, user_id)
    if session is None or user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Session is no longer valid")
    return user


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized = str(payload.email).strip().lower()
    user = User(
        email=normalized,
        email_normalized=normalized,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()
        tokens = _issue_session(db, user)
        db.commit()
        return tokens
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    # Keep the response identical for unknown accounts and incorrect passwords.
    if user is None or user.password_hash is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled")
    tokens = _issue_session(db, user)
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_hash = hash_refresh_token(payload.refresh_token)
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(UTC),
        ).with_for_update()
    )
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    session.revoked_at = datetime.now(UTC)
    session.last_used_at = datetime.now(UTC)
    tokens = _issue_session(db, user)
    db.commit()
    return tokens


@router.post("/logout", status_code=204)
def logout(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> None:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = jwt.decode(
        credentials.credentials,
        get_settings().jwt_secret_key,
        algorithms=[get_settings().jwt_algorithm],
    )
    session = db.get(AuthSession, uuid.UUID(payload["sid"]))
    if session is not None and session.user_id == user.id and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        email_verified=user.email_verified_at is not None,
        phone_number=user.phone_e164,
        phone_verified=user.phone_verified_at is not None,
    )


@router.post("/phone/request-code", status_code=202)
def request_phone_code() -> None:
    # Delivery must be wired to an approved SMS/WhatsApp provider before enabling this route.
    provider = get_settings().otp_delivery_provider
    if provider == "unconfigured":
        raise HTTPException(
            status_code=503,
            detail="Phone verification delivery is not configured yet",
        )
    raise HTTPException(status_code=501, detail="Configured OTP provider adapter is not implemented")


@router.post("/phone/verify-code", response_model=TokenResponse)
def verify_phone_code() -> None:
    raise HTTPException(status_code=501, detail="Phone OTP verification will be enabled with the delivery adapter")
