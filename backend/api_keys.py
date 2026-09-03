"""
api_keys.py — API Key management router.

Endpoints:
  POST   /api-keys/        — Create new API key
  GET    /api-keys/        — List all API keys for current merchant
  DELETE /api-keys/{id}    — Revoke an API key
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

import database
from auth_models import ApiKeyCreatedResponse, ApiKeyListItem, CreateApiKeyRequest
from security import get_current_merchant, require_role, sha256_hex

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["API Key Management"])

_KEY_PREFIX = "rzr_live_"


def _generate_raw_key() -> str:
    """Generate a cryptographically secure 40-char API key."""
    return _KEY_PREFIX + secrets.token_hex(20)


# ---------------------------------------------------------------------------
# POST /api-keys/
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key for server-to-server access",
)
async def create_api_key(
    body: CreateApiKeyRequest,
    merchant: dict = Depends(require_role("ADMIN")),
) -> ApiKeyCreatedResponse:
    raw_key = _generate_raw_key()
    key_hash = sha256_hex(raw_key)

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    api_key = database.create_api_key(
        user_id=merchant["merchant_id"],
        label=body.label,
        raw_key=raw_key,
        key_hash=key_hash,
        expires_at=expires_at,
    )

    logger.info("API key created: %s for merchant %s", api_key.key_prefix, merchant["merchant_id"])

    return ApiKeyCreatedResponse(
        id=api_key.id,
        label=api_key.label,
        raw_key=raw_key,  # ⚠ Only shown once — merchant must copy this
        prefix=api_key.key_prefix,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


# ---------------------------------------------------------------------------
# GET /api-keys/
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=list[ApiKeyListItem],
    summary="List all API keys (partial key display — full key never re-shown)",
)
async def list_api_keys(
    merchant: dict = Depends(require_role("ADMIN")),
) -> list[ApiKeyListItem]:
    keys = database.list_api_keys(merchant["merchant_id"])
    return [
        ApiKeyListItem(
            id=k.id,
            label=k.label,
            prefix=k.key_prefix + "...",
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


# ---------------------------------------------------------------------------
# DELETE /api-keys/{key_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/{key_id}",
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: str,
    merchant: dict = Depends(require_role("ADMIN")),
) -> dict:
    success = database.revoke_api_key(key_id, merchant["merchant_id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or does not belong to your account.",
        )
    logger.info("API key revoked: %s by merchant %s", key_id, merchant["merchant_id"])
    return {"status": "success", "message": f"API key {key_id!r} has been revoked."}
