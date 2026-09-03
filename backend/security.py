"""
security.py — Core security utilities.

Responsibilities:
- Password hashing & verification (argon2-cffi — modern, no 72-byte limit)
- JWT access token & refresh token creation/decoding (python-jose)
- FastAPI dependencies: get_current_merchant, require_role
- Razorpay webhook HMAC-SHA256 signature verification
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_please_generate_a_secure_32byte_hex")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ---------------------------------------------------------------------------
# Password hashing — argon2 (modern, no 72-byte limit, bcrypt-compat-free)
# ---------------------------------------------------------------------------
_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ---------------------------------------------------------------------------
# Generic sha256 hashing for API keys and refresh tokens
# ---------------------------------------------------------------------------
def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------------------
# JWT Token utilities
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT. Raises HTTPException on failure.
    Returns the full payload dict.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI Bearer + API-Key dual auth schemes
# ---------------------------------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_merchant(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Security(api_key_header),
) -> dict:
    """
    FastAPI dependency: resolves the authenticated merchant from either:
      - Bearer JWT access token, OR
      - X-API-Key header (server-to-server access)

    Returns the merchant identity dict: { merchant_id, email, role }
    """
    # Import here to avoid circular imports
    from database import SessionLocal, User, ApiKey

    # --- 1. Try Bearer JWT ---
    if credentials and credentials.scheme.lower() == "bearer":
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type.")
        return {
            "merchant_id": payload["sub"],
            "email": payload.get("email", ""),
            "role": payload.get("role", "ANALYST"),
        }

    # --- 2. Try X-API-Key ---
    if x_api_key:
        key_hash = sha256_hex(x_api_key)
        db = SessionLocal()
        try:
            api_key_record = (
                db.query(ApiKey)
                .filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
                .first()
            )
            if api_key_record:
                # Update last_used_at
                api_key_record.last_used_at = datetime.now(timezone.utc)
                db.commit()
                user = db.query(User).filter(User.id == api_key_record.user_id).first()
                return {
                    "merchant_id": str(api_key_record.user_id),
                    "email": user.email if user else "",
                    "role": user.role if user else "ANALYST",
                }
        finally:
            db.close()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory for RBAC.
    Usage: Depends(require_role("ADMIN", "ANALYST"))
    """
    async def _check(merchant: dict = Depends(get_current_merchant)) -> dict:
        if merchant["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}. Your role: {merchant['role']}",
            )
        return merchant
    return _check


# ---------------------------------------------------------------------------
# Razorpay Webhook Signature Verification
# ---------------------------------------------------------------------------
def verify_razorpay_signature(
    raw_body: bytes,
    signature: str,
    webhook_secret: str,
) -> bool:
    """
    Verify Razorpay webhook HMAC-SHA256 signature.
    https://razorpay.com/docs/webhooks/validate-test/
    """
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)



def enforce_webhook_signature(
    raw_body: bytes,
    x_razorpay_signature: Optional[str],
    webhook_secret: str,
    skip_in_test: bool = False,
) -> None:
    """
    Raises 403 if webhook signature is invalid.
    In development/test mode, can be skipped via ENVIRONMENT env var.
    """
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "development" or skip_in_test:
        return  # Skip validation in dev/test
    if not x_razorpay_signature:
        raise HTTPException(status_code=403, detail="Missing X-Razorpay-Signature header.")
    if not verify_razorpay_signature(raw_body, x_razorpay_signature, webhook_secret):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")
