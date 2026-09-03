"""
database.py — SQLAlchemy 2.0 ORM with PostgreSQL / SQLite support.

Tables:
  merchants    — legacy compatibility alias for User (kept for existing code)
  users        — full merchant auth accounts
  api_keys     — per-merchant programmatic API keys
  refresh_tokens — JWT refresh token store (rotated on use)
  recovery_audit_log — complete decision ledger
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Index,
    Integer, String, Text, UniqueConstraint, func, create_engine,
)
from sqlalchemy.dialects.sqlite import TEXT as SQLITE_TEXT
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from models import FailedPaymentEvent, paise_to_rupees as paise_to_inr

# ---------------------------------------------------------------------------
# Engine setup
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///recovery_audit.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

is_sqlite = "sqlite" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=not is_sqlite,
    connect_args={"check_same_thread": False} if is_sqlite else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# User (Merchant) Auth Table
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    business_name = Column(String(100), nullable=False, default="My Store")
    role = Column(
        Enum("ADMIN", "ANALYST", "VIEWER", name="user_role"),
        nullable=False,
        default="ADMIN",
    )
    is_active = Column(Boolean, default=True)

    # Merchant credentials (stored per-tenant)
    razorpay_key_id = Column(String(100), nullable=True)
    razorpay_key_secret = Column(String(100), nullable=True)
    gemini_api_key = Column(String(150), nullable=True)
    webhook_secret = Column(String(100), nullable=False, default=lambda: secrets.token_hex(32))
    auto_recovery_enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Parent FK for sub-users (ANALYST/VIEWER belong to an ADMIN)
    parent_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    recovery_logs = relationship("RecoveryAuditLog", back_populates="user",
                                 foreign_keys="RecoveryAuditLog.merchant_id")


# Alias for legacy code compatibility
Merchant = User


# ---------------------------------------------------------------------------
# API Keys Table
# ---------------------------------------------------------------------------
class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    label = Column(String(80), nullable=False)
    key_prefix = Column(String(16), nullable=False)  # First 16 chars (display only)
    key_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 of raw key
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_key_hash", "key_hash"),
        Index("ix_api_key_user_active", "user_id", "is_active"),
    )


# ---------------------------------------------------------------------------
# Refresh Tokens Table (JWT rotation)
# ---------------------------------------------------------------------------
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_token_hash", "token_hash"),
        Index("ix_refresh_user_id", "user_id"),
    )


# ---------------------------------------------------------------------------
# Recovery Audit Log
# ---------------------------------------------------------------------------
class RecoveryAuditLog(Base):
    __tablename__ = "recovery_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String(36), ForeignKey("users.id"), nullable=False, default="system")
    order_id = Column(String(100), nullable=False, index=True)
    payment_id = Column(String(100), nullable=True)
    amount_paise = Column(Integer, nullable=False)
    error_code = Column(String(100), nullable=False)
    customer_name = Column(String(100), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    customer_tier = Column(String(30), default="STANDARD")
    attempts = Column(Integer, default=0)

    ai_strategy = Column(String(50), nullable=False)
    final_action = Column(Text, nullable=False)
    guardrail_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)

    payment_link = Column(Text, nullable=True)
    nudge_message_sent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="recovery_logs",
                        foreign_keys=[merchant_id])

    __table_args__ = (
        Index("ix_merchant_order_idx", "merchant_id", "order_id"),
    )


# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Create all tables and seed a default ADMIN user if none exists."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Only seed if the table is empty
        if db.query(User).count() == 0:
            from security import hash_password
            default_admin = User(
                id="default_merchant",
                email=os.getenv("DEFAULT_ADMIN_EMAIL", "admin@razorpay-recovery.local"),
                hashed_password=hash_password(
                    os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminPass@2026!")
                ),
                business_name="Default Merchant (Seeded)",
                role="ADMIN",
                razorpay_key_id=os.getenv("RAZORPAY_KEY_ID"),
                razorpay_key_secret=os.getenv("RAZORPAY_KEY_SECRET"),
                gemini_api_key=os.getenv("GEMINI_API_KEY"),
                auto_recovery_enabled=True,
            )
            db.add(default_admin)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CRUD helpers — Auth
# ---------------------------------------------------------------------------
def get_user_by_email(email: str) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email.lower()).first()
    finally:
        db.close()


def get_user_by_id(user_id: str) -> Optional[User]:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


def create_user(
    email: str,
    hashed_password: str,
    business_name: str,
    role: str = "ADMIN",
    razorpay_key_id: Optional[str] = None,
    razorpay_key_secret: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> User:
    db = SessionLocal()
    try:
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            business_name=business_name,
            role=role,
            razorpay_key_id=razorpay_key_id,
            razorpay_key_secret=razorpay_key_secret,
            gemini_api_key=gemini_api_key,
            parent_id=parent_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CRUD helpers — Refresh Tokens
# ---------------------------------------------------------------------------
def store_refresh_token(user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
    db = SessionLocal()
    try:
        rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        db.add(rt)
        db.commit()
        db.refresh(rt)
        return rt
    finally:
        db.close()


def get_refresh_token(token_hash: str) -> Optional[RefreshToken]:
    db = SessionLocal()
    try:
        return (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )
    finally:
        db.close()


def revoke_refresh_token(token_hash: str) -> None:
    db = SessionLocal()
    try:
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if rt:
            rt.revoked = True
            db.commit()
    finally:
        db.close()


def revoke_all_refresh_tokens(user_id: str) -> None:
    """Revoke all tokens for a user (e.g. password change or security event)."""
    db = SessionLocal()
    try:
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CRUD helpers — API Keys
# ---------------------------------------------------------------------------
def create_api_key(
    user_id: str,
    label: str,
    raw_key: str,
    key_hash: str,
    expires_at: Optional[datetime] = None,
) -> ApiKey:
    db = SessionLocal()
    try:
        api_key = ApiKey(
            user_id=user_id,
            label=label,
            key_prefix=raw_key[:16],
            key_hash=key_hash,
            expires_at=expires_at,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key
    finally:
        db.close()


def list_api_keys(user_id: str) -> list[ApiKey]:
    db = SessionLocal()
    try:
        return (
            db.query(ApiKey)
            .filter(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )
    finally:
        db.close()


def get_api_key(key_id: str, user_id: str) -> Optional[ApiKey]:
    db = SessionLocal()
    try:
        return (
            db.query(ApiKey)
            .filter(ApiKey.id == key_id, ApiKey.user_id == user_id)
            .first()
        )
    finally:
        db.close()


def revoke_api_key(key_id: str, user_id: str) -> bool:
    db = SessionLocal()
    try:
        key = db.query(ApiKey).filter(
            ApiKey.id == key_id, ApiKey.user_id == user_id
        ).first()
        if not key:
            return False
        key.is_active = False
        db.commit()
        return True
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Legacy Recovery Pipeline helpers (unchanged interface)
# ---------------------------------------------------------------------------
def is_order_active_or_resolved(order_id: str, merchant_id: str = "default_merchant") -> bool:
    db = SessionLocal()
    try:
        res = (
            db.query(RecoveryAuditLog.id)
            .filter(
                RecoveryAuditLog.order_id == order_id,
                RecoveryAuditLog.merchant_id == merchant_id,
            )
            .first()
        )
        return res is not None
    finally:
        db.close()


# Alias
is_order_locked_or_resolved = is_order_active_or_resolved


def log_recovery(
    event: FailedPaymentEvent,
    ai_strategy: str,
    final_action: str,
    overridden: bool,
    override_reason: Optional[str] = None,
    payment_link_url: Optional[str] = None,
    status: str = "RECOVERED_PENDING_PAYMENT",
    merchant_id: str = "default_merchant",
    nudge_sent: Optional[str] = None,
    link: Optional[str] = None,
    **kwargs,
) -> None:
    db = SessionLocal()
    try:
        entry = RecoveryAuditLog(
            merchant_id=merchant_id,
            order_id=event.order_id,
            payment_id=event.payment_id,
            amount_paise=event.amount,
            error_code=event.error_code,
            customer_name=event.customer_name,
            customer_phone=event.customer_phone,
            customer_tier=event.customer_tier,
            attempts=event.attempts_made,
            ai_strategy=ai_strategy,
            final_action=final_action,
            guardrail_override=overridden,
            override_reason=override_reason,
            status=status,
            payment_link=payment_link_url or link,
            nudge_message_sent=nudge_sent,
        )
        db.add(entry)
        db.commit()
    finally:
        db.close()


def get_metrics(merchant_id: Optional[str] = None) -> dict:
    db = SessionLocal()
    try:
        q = db.query(RecoveryAuditLog)
        if merchant_id:
            q = q.filter(RecoveryAuditLog.merchant_id == merchant_id)

        total_events = q.count()
        total_paise = q.with_entities(func.coalesce(func.sum(RecoveryAuditLog.amount_paise), 0)).scalar() or 0
        recovered_paise = (
            q.filter(RecoveryAuditLog.status == "RECOVERED_PENDING_PAYMENT")
            .with_entities(func.coalesce(func.sum(RecoveryAuditLog.amount_paise), 0))
            .scalar() or 0
        )
        scheduled_paise = (
            q.filter(RecoveryAuditLog.status == "SCHEDULED_RETRY")
            .with_entities(func.coalesce(func.sum(RecoveryAuditLog.amount_paise), 0))
            .scalar() or 0
        )
        aborted_paise = (
            q.filter(RecoveryAuditLog.status == "ABORTED")
            .with_entities(func.coalesce(func.sum(RecoveryAuditLog.amount_paise), 0))
            .scalar() or 0
        )
        override_count = q.filter(RecoveryAuditLog.guardrail_override == True).count()
        success_count = q.filter(
            RecoveryAuditLog.status.in_(["RECOVERED_PENDING_PAYMENT", "SCHEDULED_RETRY"])
        ).count()
        recovery_rate = round((success_count / total_events * 100), 2) if total_events else 0.0

        return {
            "total_events_processed": total_events,
            "total_gmv_at_risk_inr": paise_to_inr(total_paise),
            "total_gmv_recovered_inr": paise_to_inr(recovered_paise),
            "total_gmv_recovering_inr": paise_to_inr(recovered_paise),
            "total_gmv_scheduled_inr": paise_to_inr(scheduled_paise),
            "total_gmv_aborted_inr": paise_to_inr(aborted_paise),
            "guardrail_override_count": override_count,
            "guardrail_overrides": override_count,
            "recovery_success_rate_pct": recovery_rate,
        }
    finally:
        db.close()


def get_recent_logs(limit: int = 20, merchant_id: Optional[str] = None) -> list[dict]:
    db = SessionLocal()
    try:
        q = db.query(RecoveryAuditLog)
        if merchant_id:
            q = q.filter(RecoveryAuditLog.merchant_id == merchant_id)
        rows = q.order_by(RecoveryAuditLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "merchant_id": r.merchant_id,
                "order_id": r.order_id,
                "payment_id": r.payment_id,
                "amount_inr": paise_to_inr(r.amount_paise),
                "error_code": r.error_code,
                "customer_name": r.customer_name,
                "customer_phone": r.customer_phone,
                "customer_tier": r.customer_tier,
                "attempts": r.attempts,
                "ai_strategy": r.ai_strategy,
                "final_action": r.final_action,
                "guardrail_overridden": r.guardrail_override,
                "override_reason": r.override_reason,
                "payment_link_url": r.payment_link,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def reset_db(merchant_id: Optional[str] = None) -> None:
    db = SessionLocal()
    try:
        if merchant_id:
            db.query(RecoveryAuditLog).filter(
                RecoveryAuditLog.merchant_id == merchant_id
            ).delete()
        else:
            db.query(RecoveryAuditLog).delete()
        db.commit()
    finally:
        db.close()
