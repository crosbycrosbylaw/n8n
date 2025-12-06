from __future__ import annotations

import typing

__all__ = ['record_factory']

from datetime import UTC, datetime
from uuid import uuid4

if typing.TYPE_CHECKING:
    from eserv.types import EmailInfo, EmailRecord


@typing.overload
def record_factory(
    *,
    uid: str | None = None,
    sender: str = 'unknown',
    subject: str = '',
) -> EmailInfo: ...
@typing.overload
def record_factory(
    body: str,
    *,
    uid: str | None = None,
    received_at: datetime | None = None,
    subject: str = '',
    sender: str = 'unknown',
) -> EmailRecord: ...
def record_factory(
    body: ... = None,
    *,
    uid: str | None = None,
    received_at: datetime | None = None,
    subject: str = '',
    sender: str = 'unknown',
) -> ...:
    """Initialize a new email record, with sensible defaults."""
    from eserv.types.structs import EmailInfo, EmailRecord

    uid = uid or str(uuid4())

    if body is None:
        return EmailInfo(uid=uid, sender=sender, subject=subject)

    return EmailRecord(uid or str(uuid4()), sender, subject, received_at or datetime.now(UTC), body)
