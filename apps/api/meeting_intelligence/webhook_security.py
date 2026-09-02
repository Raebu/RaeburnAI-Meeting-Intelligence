from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, String, delete, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from meeting_intelligence.config import Settings
from meeting_intelligence.storage import Base, _build_engine

_DEFAULT_MAX_AGE_SECONDS = 300


class WebhookReceiptRecord(Base):
    __tablename__ = "webhook_receipts"

    workspace_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    body_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


def verify_inbound_signature(
    *,
    body: bytes,
    signing_secret: str,
    timestamp: str,
    signature: str,
    now: int | None = None,
    max_age_seconds: int = _DEFAULT_MAX_AGE_SECONDS,
) -> bool:
    """Verify HMAC-SHA256 signature and reject stale/future webhook timestamps."""
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        return False
    reference_time = int(time.time()) if now is None else now
    if abs(reference_time - timestamp_value) > max_age_seconds:
        return False
    if not signature.startswith("sha256="):
        return False
    supplied = signature.removeprefix("sha256=")
    message = str(timestamp_value).encode() + b"." + body
    expected = hmac.new(signing_secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


class WebhookReplayStore:
    """Persist inbound webhook event IDs so duplicate delivery cannot be replayed."""

    def __init__(self, settings: Settings, *, retention_seconds: int = 86_400) -> None:
        self._engine = _build_engine(settings.database_url)
        self._environment = settings.environment
        self._retention_seconds = retention_seconds

    def bootstrap_nonproduction_schema(self) -> None:
        if self._environment != "production":
            Base.metadata.create_all(self._engine)

    def ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM webhook_receipts LIMIT 1"))
            return True
        except Exception:
            return False

    def record_once(self, workspace_id: str, event_id: str, body: bytes) -> bool:
        if not workspace_id or not event_id:
            raise ValueError("workspace_id and event_id are required")
        now = datetime.now(UTC)
        digest = hashlib.sha256(body).hexdigest()
        with Session(self._engine) as session:
            existing = session.scalar(
                select(WebhookReceiptRecord).where(
                    WebhookReceiptRecord.workspace_id == workspace_id,
                    WebhookReceiptRecord.event_id == event_id,
                )
            )
            if existing is not None:
                return False
            session.add(
                WebhookReceiptRecord(
                    workspace_id=workspace_id,
                    event_id=event_id,
                    body_digest=digest,
                    received_at=now,
                )
            )
            session.commit()
        return True

    def prune_expired(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=self._retention_seconds)
        with Session(self._engine) as session:
            result = session.execute(
                delete(WebhookReceiptRecord).where(
                    WebhookReceiptRecord.received_at < cutoff
                )
            )
            session.commit()
            return int(result.rowcount or 0)
