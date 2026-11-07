import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decrypt_otp,
    encrypt_otp,
    hash_otp,
    hash_password,
    hash_refresh_token,
    new_otp,
    new_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.integrations.tumasend import TumaSendClient, TumaSendError
from app.models import AuthSession, PhoneOtpChallenge, User
from app.modules.identity.schemas import (
    LoginRequest,
    PhoneOtpAcceptedResponse,
    PhoneOtpRequest,
    PhoneOtpVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)
OTP_LIFETIME_MINUTES = 5
OTP_MAX_ATTEMPTS = 5


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


def _tumasend() -> TumaSendClient:
    settings = get_settings()
    return TumaSendClient(
        whatsapp_api_key=settings.tumasend_whatsapp_api_key,
        sms_api_key=settings.tumasend_sms_api_key,
        sms_sender_id=settings.tumasend_sms_sender_id,
        base_url=settings.tumasend_base_url,
    )


def _send_otp(challenge: PhoneOtpChallenge, code: str, db: Session) -> None:
    message = (
        f"Your BookFlow AI verification code is {code}. "
        f"It expires in {OTP_LIFETIME_MINUTES} minutes. Do not share this code."
    )
    try:
        client = _tumasend()
        challenge.whatsapp_batch_id = client.send_whatsapp(challenge.phone_e164, message)
        challenge.delivery_status = "whatsapp_queued"
        db.commit()
        return
    except TumaSendError:
        # An explicit API/transport failure triggers immediate SMS fallback.
        pass

    try:
        client = _tumasend()
        challenge.sms_batch_id = client.send_sms(challenge.phone_e164, message)
        challenge.delivery_status = "sms_queued"
        db.commit()
    except TumaSendError:
        challenge.delivery_status = "delivery_failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="We could not send a verification code. Please try again later.",
        ) from None


def _create_challenge(
    *,
    db: Session,
    user: User,
    phone_number: str,
    purpose: str,
) -> PhoneOtpAcceptedResponse:
    now = datetime.now(UTC)
    previous = db.scalars(
        select(PhoneOtpChallenge).where(
            PhoneOtpChallenge.phone_e164 == phone_number,
            PhoneOtpChallenge.purpose == purpose,
            PhoneOtpChallenge.consumed_at.is_(None),
        )
    ).all()
    for challenge in previous:
        challenge.consumed_at = now

    code = new_otp()
    challenge = PhoneOtpChallenge(
        user_id=user.id,
        phone_e164=phone_number,
        purpose=purpose,
        code_hash=hash_otp(phone_number, code),
        code_ciphertext=encrypt_otp(code),
        expires_at=now + timedelta(minutes=OTP_LIFETIME_MINUTES),
        delivery_status="pending",
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    _send_otp(challenge, code, db)
    return PhoneOtpAcceptedResponse(challenge_id=str(challenge.id))


def _verify_code(
    *,
    db: Session,
    payload: PhoneOtpVerifyRequest,
    purpose: str,
    expected_user: User | None = None,
) -> tuple[PhoneOtpChallenge, User]:
    try:
        challenge_id = uuid.UUID(payload.challenge_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code") from None

    challenge = db.scalar(
        select(PhoneOtpChallenge)
        .where(PhoneOtpChallenge.id == challenge_id)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if (
        challenge is None
        or challenge.purpose != purpose
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or challenge.attempts >= OTP_MAX_ATTEMPTS
        or challenge.delivery_status in {"pending", "delivery_failed"}
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    user = db.get(User, challenge.user_id) if challenge.user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    if expected_user is not None and user.id != expected_user.id:
        raise HTTPException(status_code=403, detail="This verification request belongs to another account")

    submitted_hash = hash_otp(challenge.phone_e164, payload.code)
    if not hmac.compare_digest(submitted_hash, challenge.code_hash):
        challenge.attempts += 1
        if challenge.attempts >= OTP_MAX_ATTEMPTS:
            challenge.consumed_at = now
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    challenge.consumed_at = now
    return challenge, user


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


@router.post("/phone/request-code", response_model=PhoneOtpAcceptedResponse, status_code=202)
def request_phone_code(payload: PhoneOtpRequest, db: Session = Depends(get_db)) -> PhoneOtpAcceptedResponse:
    user = db.scalar(
        select(User).where(
            User.phone_e164 == payload.phone_number,
            User.phone_verified_at.is_not(None),
            User.is_active.is_(True),
        )
    )
    # Avoid revealing whether a phone number is registered.
    if user is None:
        return PhoneOtpAcceptedResponse(challenge_id=str(uuid.uuid4()))
    return _create_challenge(db=db, user=user, phone_number=payload.phone_number, purpose="login")


@router.post("/phone/verify-code", response_model=TokenResponse)
def verify_phone_code(payload: PhoneOtpVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, user = _verify_code(db=db, payload=payload, purpose="login")
    tokens = _issue_session(db, user)
    db.commit()
    return tokens


@router.post("/phone/link/request-code", response_model=PhoneOtpAcceptedResponse, status_code=202)
def request_phone_link_code(
    payload: PhoneOtpRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PhoneOtpAcceptedResponse:
    existing = db.scalar(select(User).where(User.phone_e164 == payload.phone_number))
    if existing is not None and existing.id != user.id:
        raise HTTPException(status_code=409, detail="This phone number is already linked to an account")
    if existing is not None and existing.phone_verified_at is not None:
        raise HTTPException(status_code=409, detail="This phone number is already verified")
    return _create_challenge(db=db, user=user, phone_number=payload.phone_number, purpose="link")


@router.post("/phone/link/verify-code", response_model=UserResponse)
def verify_phone_link_code(
    payload: PhoneOtpVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    challenge, verified_user = _verify_code(
        db=db, payload=payload, purpose="link", expected_user=user
    )
    verified_user.phone_e164 = challenge.phone_e164
    verified_user.phone_verified_at = datetime.now(UTC)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This phone number is already linked") from None
    return me(verified_user)


@router.post("/webhooks/tumasend", status_code=200, include_in_schema=False)
async def tumasend_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    secret = settings.tumasend_webhook_secret
    signature = request.headers.get("X-TumaSend-Signature", "")
    raw_body = await request.body()
    if not secret:
        raise HTTPException(status_code=503, detail="Messaging webhook is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        event = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from None
    event_type = event.get("event_type")
    data = event.get("payload") or {}
    batch_id = data.get("batch_id")
    channel = data.get("channel")
    if not isinstance(batch_id, str):
        return {"status": "ignored"}

    challenge = db.scalar(
        select(PhoneOtpChallenge)
        .where(
            or_(
                PhoneOtpChallenge.whatsapp_batch_id == batch_id,
                PhoneOtpChallenge.sms_batch_id == batch_id,
            )
        )
        .with_for_update()
    )
    if challenge is None:
        return {"status": "ignored"}

    if event_type == "message.delivered":
        challenge.delivery_status = "delivered"
        db.commit()
        return {"status": "recorded"}

    if event_type == "message.failed" and channel == "whatsapp":
        if (
            challenge.sms_batch_id is None
            and challenge.consumed_at is None
            and challenge.expires_at > datetime.now(UTC)
        ):
            try:
                if not challenge.code_ciphertext:
                    raise InvalidToken
                code = decrypt_otp(challenge.code_ciphertext)
                message = (
                    f"Your BookFlow AI verification code is {code}. "
                    f"It expires in {OTP_LIFETIME_MINUTES} minutes. Do not share this code."
                )
                client = _tumasend()
                challenge.sms_batch_id = client.send_sms(challenge.phone_e164, message)
                challenge.delivery_status = "sms_queued"
            except (TumaSendError, InvalidToken):
                challenge.delivery_status = "delivery_failed"
        db.commit()
        return {"status": "fallback_attempted"}

    if event_type == "message.failed":
        challenge.delivery_status = "delivery_failed"
        db.commit()
        return {"status": "recorded"}

    return {"status": "ignored"}
