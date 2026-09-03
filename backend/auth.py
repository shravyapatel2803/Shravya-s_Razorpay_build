"""
auth.py — JWT Authentication Router.

Endpoints:
  POST /auth/register      — Merchant self-registration
  POST /auth/login         — Password login, returns access + refresh tokens
  POST /auth/refresh       — Re-issue access token from refresh token
  POST /auth/logout        — Revoke refresh token
  GET  /auth/me            — Current merchant profile
  PUT  /auth/me            — Update profile / credentials
  POST /auth/me/change-password — Change password
  POST /auth/sub-users     — [ADMIN] Create analyst/viewer sub-user
  GET  /auth/sub-users     — [ADMIN] List sub-users
  DELETE /auth/sub-users/{id} — [ADMIN] Deactivate sub-user
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

import database
from auth_models import (
    AccessTokenResponse,
    ChangePasswordRequest,
    CreateSubUserRequest,
    MerchantLoginRequest,
    MerchantProfile,
    MerchantRegisterRequest,
    RefreshRequest,
    SubUserResponse,
    TokenResponse,
    UpdateProfileRequest,
)
from security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_merchant,
    hash_password,
    require_role,
    sha256_hex,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Helper: build token pair
# ---------------------------------------------------------------------------
def _issue_token_pair(user: database.User) -> TokenResponse:
    payload = {"sub": user.id, "email": user.email, "role": user.role}

    access_token = create_access_token(payload)

    raw_refresh = secrets.token_urlsafe(64)
    refresh_hash = sha256_hex(raw_refresh)
    refresh_token = create_refresh_token(payload)

    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    database.store_refresh_token(user.id, sha256_hex(refresh_token), expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=MerchantProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Self-register a new merchant account",
)
async def register(body: MerchantRegisterRequest) -> MerchantProfile:
    if database.get_user_by_email(body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered.",
        )

    hashed = hash_password(body.password)
    user = database.create_user(
        email=body.email,
        hashed_password=hashed,
        business_name=body.business_name,
        role="ADMIN",
        razorpay_key_id=body.razorpay_key_id,
        razorpay_key_secret=body.razorpay_key_secret,
        gemini_api_key=body.gemini_api_key,
    )
    logger.info("Registered new merchant: %s (%s)", user.email, user.id)

    return MerchantProfile(
        id=user.id,
        email=user.email,
        business_name=user.business_name,
        role=user.role,
        is_active=user.is_active,
        razorpay_key_id=user.razorpay_key_id,
        gemini_api_key_configured=bool(user.gemini_api_key),
        auto_recovery_enabled=user.auto_recovery_enabled,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive access + refresh tokens",
)
async def login(body: MerchantLoginRequest) -> TokenResponse:
    user = database.get_user_by_email(body.email)
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended. Contact support.",
        )

    logger.info("Merchant login: %s", user.email)
    return _issue_token_pair(user)


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh access token using a valid refresh token",
)
async def refresh_token(body: RefreshRequest) -> AccessTokenResponse:
    # Decode refresh token to get claims (also validates expiry & signature)
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type.")

    # Verify it's stored and not revoked
    token_hash = sha256_hex(body.refresh_token)
    stored = database.get_refresh_token(token_hash)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid, expired, or revoked.",
        )

    user = database.get_user_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Account not found or suspended.")

    # Rotate: revoke old, issue new access token
    database.revoke_refresh_token(token_hash)
    new_access = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    return AccessTokenResponse(
        access_token=new_access,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout", summary="Revoke refresh token (logout)")
async def logout(body: RefreshRequest) -> dict:
    token_hash = sha256_hex(body.refresh_token)
    database.revoke_refresh_token(token_hash)
    return {"status": "success", "message": "Logged out successfully."}


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=MerchantProfile,
    summary="Get current merchant profile",
)
async def get_me(merchant: dict = Depends(get_current_merchant)) -> MerchantProfile:
    user = database.get_user_by_id(merchant["merchant_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return MerchantProfile(
        id=user.id,
        email=user.email,
        business_name=user.business_name,
        role=user.role,
        is_active=user.is_active,
        razorpay_key_id=user.razorpay_key_id,
        gemini_api_key_configured=bool(user.gemini_api_key),
        auto_recovery_enabled=user.auto_recovery_enabled,
        created_at=user.created_at,
    )


# ---------------------------------------------------------------------------
# PUT /auth/me — Update profile
# ---------------------------------------------------------------------------
@router.put("/me", response_model=MerchantProfile, summary="Update merchant profile / credentials")
async def update_me(
    body: UpdateProfileRequest,
    merchant: dict = Depends(get_current_merchant),
) -> MerchantProfile:
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter(database.User.id == merchant["merchant_id"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if body.business_name is not None:
            user.business_name = body.business_name
        if body.razorpay_key_id is not None:
            user.razorpay_key_id = body.razorpay_key_id
        if body.razorpay_key_secret is not None:
            user.razorpay_key_secret = body.razorpay_key_secret
        if body.gemini_api_key is not None:
            user.gemini_api_key = body.gemini_api_key
        if body.auto_recovery_enabled is not None:
            user.auto_recovery_enabled = body.auto_recovery_enabled

        db.commit()
        db.refresh(user)

        return MerchantProfile(
            id=user.id,
            email=user.email,
            business_name=user.business_name,
            role=user.role,
            is_active=user.is_active,
            razorpay_key_id=user.razorpay_key_id,
            gemini_api_key_configured=bool(user.gemini_api_key),
            auto_recovery_enabled=user.auto_recovery_enabled,
            created_at=user.created_at,
        )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# POST /auth/me/change-password
# ---------------------------------------------------------------------------
@router.post("/me/change-password", summary="Change account password")
async def change_password(
    body: ChangePasswordRequest,
    merchant: dict = Depends(get_current_merchant),
) -> dict:
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter(database.User.id == merchant["merchant_id"]).first()
        if not user or not verify_password(body.current_password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Current password is incorrect.")

        user.hashed_password = hash_password(body.new_password)
        db.commit()

    finally:
        db.close()

    # Revoke all refresh tokens to force re-login on all devices
    database.revoke_all_refresh_tokens(merchant["merchant_id"])
    return {"status": "success", "message": "Password updated. Please login again."}


# ---------------------------------------------------------------------------
# Sub-User Management (ADMIN only)
# ---------------------------------------------------------------------------
@router.post(
    "/sub-users",
    response_model=SubUserResponse,
    status_code=201,
    summary="[ADMIN] Create an Analyst or Viewer sub-user",
)
async def create_sub_user(
    body: CreateSubUserRequest,
    merchant: dict = Depends(require_role("ADMIN")),
) -> SubUserResponse:
    if database.get_user_by_email(body.email):
        raise HTTPException(status_code=409, detail=f"Email '{body.email}' already exists.")

    user = database.create_user(
        email=body.email,
        hashed_password=hash_password(body.password),
        business_name="",
        role=body.role,
        parent_id=merchant["merchant_id"],
    )
    return SubUserResponse(
        id=user.id, email=user.email,
        role=user.role, is_active=user.is_active, created_at=user.created_at,
    )


@router.get(
    "/sub-users",
    response_model=list[SubUserResponse],
    summary="[ADMIN] List all sub-users",
)
async def list_sub_users(merchant: dict = Depends(require_role("ADMIN"))) -> list[SubUserResponse]:
    db = database.SessionLocal()
    try:
        users = (
            db.query(database.User)
            .filter(database.User.parent_id == merchant["merchant_id"])
            .all()
        )
        return [
            SubUserResponse(
                id=u.id, email=u.email,
                role=u.role, is_active=u.is_active, created_at=u.created_at,
            )
            for u in users
        ]
    finally:
        db.close()


@router.delete("/sub-users/{user_id}", summary="[ADMIN] Deactivate a sub-user")
async def deactivate_sub_user(
    user_id: str,
    merchant: dict = Depends(require_role("ADMIN")),
) -> dict:
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter(
            database.User.id == user_id,
            database.User.parent_id == merchant["merchant_id"],
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="Sub-user not found.")
        user.is_active = False
        db.commit()
        database.revoke_all_refresh_tokens(user_id)
        return {"status": "success", "message": f"Sub-user {user.email} deactivated."}
    finally:
        db.close()
