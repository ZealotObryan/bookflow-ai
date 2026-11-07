import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import auth_rate_limit
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
from app.integrations.email import EmailDeliveryError, send_transactional_email
from app.integrations.tumasend import TumaSendClient, TumaSendError
from app.models import AuthSession, AuthToken, PhoneOtpChallenge, User
from app.modules.identity.schemas import (
    ChangePasswordRequest,
    EmailRequest,
    EmailTokenRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetRequest,
    PhoneOtpAcceptedResponse,
    PhoneOtpRequest,
    PhoneOtpVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer(auto_error=False)
OTP_LIFETIME_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
EMAIL_VERIFICATION_PURPOSE = "verify_email"
PASSWORD_RESET_PURPOSE = "password_reset"
GENERIC_EMAIL_MESSAGE = "If the address is eligible, instructions will be sent to it."
_DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


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


def _decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["exp", "iat", "sub", "sid", "iss", "aud", "jti"]},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = _decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload["sid"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from None

    now = datetime.now(UTC)
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        ).with_for_update()
    )
    user = db.get(User, user_id)
    if session is None or user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Session is no longer valid")

    idle_anchor = session.last_used_at or session.created_at
    idle_limit = timedelta(minutes=get_settings().session_idle_timeout_minutes)
    if idle_anchor < now - idle_limit:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired due to inactivity")

    session.last_used_at = now
    db.commit()
    return user


def _email_configured() -> bool:
    settings = get_settings()
    return all([settings.smtp_host, settings.smtp_username, settings.smtp_password, settings.smtp_from_email])


def _create_email_token(db: Session, user: User, purpose: str) -> str:
    now = datetime.now(UTC)
    previous = db.scalars(
        select(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.consumed_at.is_(None),
        )
        .with_for_update()
    ).all()
    for old_token in previous:
        old_token.consumed_at = now

    raw_token = secrets.token_urlsafe(48)
    if purpose == EMAIL_VERIFICATION_PURPOSE:
        expires = now + timedelta(hours=get_settings().email_verification_hours)
    else:
        expires = now + timedelta(minutes=get_settings().password_reset_minutes)
    db.add(
        AuthToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_token),
            purpose=purpose,
            expires_at=expires,
        )
    )
    db.commit()
    return raw_token


def _send_auth_email(user: User, raw_token: str, purpose: str) -> None:
    settings = get_settings()
    if purpose == EMAIL_VERIFICATION_PURPOSE:
        subject = "Verify your BookFlow AI email address"
        url = f"{settings.frontend_base_url.rstrip('/')}/auth/verify-email#token={raw_token}"
        body = (
            f"Hello {user.full_name},\n\n"
            "Please verify your email address to activate your BookFlow AI sign-in.\n\n"
            f"{url}\n\n"
            f"This link expires in {settings.email_verification_hours} hours. "
            "If you did not create this account, you can ignore this email."
        )
    else:
        subject = "Reset your BookFlow AI password"
        url = f"{settings.frontend_base_url.rstrip('/')}/auth/reset-password#token={raw_token}"
        body = (
            f"Hello {user.full_name},\n\n"
            "A password reset was requested for your BookFlow AI account.\n\n"
            f"{url}\n\n"
            f"This link expires in {settings.password_reset_minutes} minutes. "
            "If you did not request this, ignore this email and consider reviewing your active sessions."
        )
    send_transactional_email(recipient=user.email, subject=subject, text_body=body)


def _request_auth_email(user: User, purpose: str, db: Session) -> None:
    raw_token = _create_email_token(db, user, purpose)
    try:
        _send_auth_email(user, raw_token, purpose)
    except EmailDeliveryError:
        # Do not log addresses, token values, or full verification/reset URLs.
        logger.error("Transactional auth email delivery failed for purpose=%s", purpose)


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
        pass

    try:
        client = _tumasend()
        challenge.sms_batch_id = client.send_sms(challenge.phone_e164, message)
        challenge.delivery_status = "sms_queued"
        db.commit()
    except TumaSendError:
        challenge.delivery_status = "delivery_failed"
        challenge.code_ciphertext = None
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
        select(PhoneOtpChallenge)
        .where(
            PhoneOtpChallenge.phone_e164 == phone_number,
            PhoneOtpChallenge.purpose == purpose,
            PhoneOtpChallenge.consumed_at.is_(None),
        )
        .with_for_update()
    ).all()
    for challenge in previous:
        challenge.consumed_at = now
        challenge.code_ciphertext = None

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
        or challenge.delivery_status in {"pending", "delivery_failed", "sms_failed"}
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
            challenge.code_ciphertext = None
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    challenge.consumed_at = now
    challenge.code_ciphertext = None
    return challenge, user


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=202,
    dependencies=[Depends(auth_rate_limit("register", ip_limit=5, ip_window=3600))],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> MessageResponse:
    if not _email_configured():
        raise HTTPException(status_code=503, detail="Account registration is temporarily unavailable")
    normalized = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    if user is None:
        user = User(
            email=normalized,
            email_normalized=normalized,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        try:
            db.flush()
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.scalar(select(User).where(User.email_normalized == normalized))
    if user is not None and user.email_verified_at is None and user.is_active:
        _request_auth_email(user, EMAIL_VERIFICATION_PURPOSE, db)
    return MessageResponse(message="If the address can be registered, a verification email will be sent.")


@router.post(
    "/email/resend-verification",
    response_model=MessageResponse,
    status_code=202,
    dependencies=[
        Depends(auth_rate_limit("email-verify-resend", ip_limit=10, ip_window=3600, identifier_limit=3, identifier_window=3600, identifier_field="email"))
    ],
)
def resend_email_verification(payload: EmailRequest, db: Session = Depends(get_db)) -> MessageResponse:
    if not _email_configured():
        raise HTTPException(status_code=503, detail="Email service is temporarily unavailable")
    normalized = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    if user is not None and user.email_verified_at is None and user.is_active:
        _request_auth_email(user, EMAIL_VERIFICATION_PURPOSE, db)
    return MessageResponse(message=GENERIC_EMAIL_MESSAGE)


@router.post(
    "/email/verify",
    response_model=MessageResponse,
    dependencies=[Depends(auth_rate_limit("email-verify", ip_limit=20, ip_window=900))],
)
def verify_email(payload: EmailTokenRequest, db: Session = Depends(get_db)) -> MessageResponse:
    token_hash = hash_refresh_token(payload.token)
    auth_token = db.scalar(
        select(AuthToken)
        .where(AuthToken.token_hash == token_hash, AuthToken.purpose == EMAIL_VERIFICATION_PURPOSE)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if auth_token is None or auth_token.consumed_at is not None or auth_token.expires_at <= now:
        raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
    user = db.get(User, auth_token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
    auth_token.consumed_at = now
    user.email_verified_at = now
    db.commit()
    return MessageResponse(message="Email address verified. You can now sign in.")


@router.post(
    "/password/forgot",
    response_model=MessageResponse,
    status_code=202,
    dependencies=[
        Depends(auth_rate_limit("password-forgot", ip_limit=10, ip_window=3600, identifier_limit=3, identifier_window=3600, identifier_field="email"))
    ],
)
def forgot_password(payload: EmailRequest, db: Session = Depends(get_db)) -> MessageResponse:
    if not _email_configured():
        raise HTTPException(status_code=503, detail="Password recovery is temporarily unavailable")
    normalized = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    if user is not None and user.email_verified_at is not None and user.is_active:
        _request_auth_email(user, PASSWORD_RESET_PURPOSE, db)
    return MessageResponse(message=GENERIC_EMAIL_MESSAGE)


@router.post(
    "/password/reset",
    response_model=MessageResponse,
    dependencies=[Depends(auth_rate_limit("password-reset", ip_limit=20, ip_window=900))],
)
def reset_password(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> MessageResponse:
    token_hash = hash_refresh_token(payload.token)
    auth_token = db.scalar(
        select(AuthToken)
        .where(AuthToken.token_hash == token_hash, AuthToken.purpose == PASSWORD_RESET_PURPOSE)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if auth_token is None or auth_token.consumed_at is not None or auth_token.expires_at <= now:
        raise HTTPException(status_code=400, detail="Password reset link is invalid or expired")
    user = db.get(User, auth_token.user_id)
    if user is None or not user.is_active or user.email_verified_at is None:
        raise HTTPException(status_code=400, detail="Password reset link is invalid or expired")
    auth_token.consumed_at = now
    user.password_hash = hash_password(payload.new_password)
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == PASSWORD_RESET_PURPOSE,
            AuthToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    db.commit()
    return MessageResponse(message="Password updated. Please sign in again.")


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[
        Depends(auth_rate_limit("login", ip_limit=30, ip_window=900, identifier_limit=5, identifier_window=900, identifier_field="email"))
    ],
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    normalized = str(payload.email).strip().casefold()
    user = db.scalar(select(User).where(User.email_normalized == normalized))
    password_hash = user.password_hash if user is not None and user.password_hash else _DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if (
        user is None
        or not password_valid
        or not user.is_active
        or user.email_verified_at is None
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    tokens = _issue_session(db, user)
    db.commit()
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limit("refresh", ip_limit=30, ip_window=900))],
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token_hash = hash_refresh_token(payload.refresh_token)
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.refresh_token_hash == token_hash)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if session.revoked_at is not None:
        db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == session.user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Session security check failed; please sign in again")
    if session.expires_at <= now:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active or user.email_verified_at is None:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail="Account is unavailable")

    session.revoked_at = now
    session.last_used_at = now
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
    try:
        payload = _decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token") from None
    session = db.get(AuthSession, uuid.UUID(payload["sid"]))
    if session is not None and session.user_id == user.id and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()


@router.post("/logout-all", status_code=204)
def logout_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()


@router.post("/password/change", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if user.password_hash is None or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="Choose a password different from your current password")
    user.password_hash = hash_password(payload.new_password)
    now = datetime.now(UTC)
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now)
    )
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


@router.post(
    "/phone/request-code",
    response_model=PhoneOtpAcceptedResponse,
    status_code=202,
    dependencies=[
        Depends(auth_rate_limit("phone-request", ip_limit=10, ip_window=900, identifier_limit=3, identifier_window=900, identifier_field="phone_number"))
    ],
)
def request_phone_code(payload: PhoneOtpRequest, db: Session = Depends(get_db)) -> PhoneOtpAcceptedResponse:
    user = db.scalar(
        select(User).where(
            User.phone_e164 == payload.phone_number,
            User.phone_verified_at.is_not(None),
            User.is_active.is_(True),
        )
    )
    if user is None:
        return PhoneOtpAcceptedResponse(challenge_id=str(uuid.uuid4()))
    return _create_challenge(db=db, user=user, phone_number=payload.phone_number, purpose="login")


@router.post(
    "/phone/verify-code",
    response_model=TokenResponse,
    dependencies=[Depends(auth_rate_limit("phone-verify", ip_limit=15, ip_window=900, identifier_limit=5, identifier_window=900, identifier_field="challenge_id"))],
)
def verify_phone_code(payload: PhoneOtpVerifyRequest, db: Session = Depends(get_db)) -> TokenResponse:
    _, user = _verify_code(db=db, payload=payload, purpose="login")
    tokens = _issue_session(db, user)
    db.commit()
    return tokens


@router.post(
    "/phone/link/request-code",
    response_model=PhoneOtpAcceptedResponse,
    status_code=202,
    dependencies=[
        Depends(auth_rate_limit("phone-link", ip_limit=10, ip_window=900, identifier_limit=3, identifier_window=900, identifier_field="phone_number"))
    ],
)
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


@router.post(
    "/phone/link/verify-code",
    response_model=UserResponse,
    dependencies=[Depends(auth_rate_limit("phone-link-verify", ip_limit=15, ip_window=900, identifier_limit=5, identifier_window=900, identifier_field="challenge_id"))],
)
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
    if not isinstance(event, dict) or not isinstance(event.get("payload", {}), dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")
    event_type = event.get("event_type)
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
        challenge.code_ciphertext = None
        db.commit()
        return {"status": "recorded"}

    if event_type == "message.failed" and channel == "whatsapp":
        if (
            challenge.delivery_status == "whatsapp_queued"
            and challenge.sms_batch_id is None
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
                challenge.delivery_status = "sms_failed"
                challenge.code_ciphertext = None
        db.commit()
        return {"status": "fallback_attempted"}

    if event_type == "message.failed":
        challenge.delivery_status = "delivery_failed"
        challenge.code_ciphertext = None
        db.commit()
        return {"status": "recorded"}

    return {"status": "ignored"}
