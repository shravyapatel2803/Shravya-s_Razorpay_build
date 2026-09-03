"""
auth_models.py — Pydantic v2 schemas for authentication and user management.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Registration & Login
# ---------------------------------------------------------------------------
class MerchantRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    business_name: str = Field(min_length=2, max_length=100)
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    gemini_api_key: Optional[str] = None

    model_config = {"json_schema_extra": {
        "example": {
            "email": "founder@demostore.in",
            "password": "SecurePass@2026",
            "business_name": "Demo Store",
            "razorpay_key_id": "rzp_test_xxx",
            "razorpay_key_secret": "your_secret",
        }
    }}


class MerchantLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expiry


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------------------------------------------------------------------------
# Merchant Profile
# ---------------------------------------------------------------------------
class MerchantProfile(BaseModel):
    id: UUID
    email: str
    business_name: str
    role: Literal["ADMIN", "ANALYST", "VIEWER"]
    is_active: bool
    razorpay_key_id: Optional[str] = None
    gemini_api_key_configured: bool = False
    auto_recovery_enabled: bool = True
    created_at: datetime


class UpdateProfileRequest(BaseModel):
    business_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    gemini_api_key: Optional[str] = None
    auto_recovery_enabled: Optional[bool] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------------------------
# Sub-user management (ADMIN only)
# ---------------------------------------------------------------------------
class CreateSubUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: Literal["ANALYST", "VIEWER"] = "ANALYST"


class SubUserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# API Key schemas
# ---------------------------------------------------------------------------
class CreateApiKeyRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80, description="Human-friendly name for this key")
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365, description="Optional expiry in days")

    model_config = {"json_schema_extra": {
        "example": {"label": "Production Webhook Server", "expires_in_days": 90}
    }}


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    label: str
    raw_key: str  # Only returned once on creation
    prefix: str
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"json_schema_extra": {
        "example": {
            "id": "...",
            "label": "Production Webhook Server",
            "raw_key": "rzr_live_a1b2c3d4...",  # Store this securely — shown once only
            "prefix": "rzr_live_a1b2",
        }
    }}


class ApiKeyListItem(BaseModel):
    id: UUID
    label: str
    prefix: str  # partial — never expose full key
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
