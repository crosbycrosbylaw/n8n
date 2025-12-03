from __future__ import annotations

__all__ = ['record_factory']

from datetime import UTC, datetime
from uuid import uuid4

from eserv.types import EmailRecord


def record_factory(
    body: str,
    *,
    received_at: datetime | None = None,
    uid: str | None = None,
    subject: str = '',
    sender: str = 'unknown',
) -> EmailRecord:
    """Initialize a new email record, with sensible defaults."""
    return EmailRecord(uid or str(uuid4()), sender, subject, received_at or datetime.now(UTC), body)
