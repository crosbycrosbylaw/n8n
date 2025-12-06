from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from eserv.types import EmailInfo, ErrorDict, ProcessedResult, ProcessedResultDict


@overload
def result_factory(*, record: EmailInfo, error: ErrorDict | None = None) -> ProcessedResult: ...
@overload
def result_factory(entry: ProcessedResultDict, /) -> ProcessedResult: ...
def result_factory(
    entry: ProcessedResultDict | None = None,
    *,
    record: EmailInfo | None = None,
    error: ErrorDict | None = None,
) -> ProcessedResult:
    """Create a ProcessedResult instance."""
    from eserv.record import record_factory
    from eserv.types import EmailInfo, ProcessedResult

    if isinstance(record, EmailInfo):
        return ProcessedResult(record=record, error=error)

    if entry is None:
        raise ValueError

    return ProcessedResult(
        record=record_factory(
            uid=entry['uid'],
            sender=entry['sender'],
            subject=entry['subject'],
        ),
        error=entry['error'],
        processed_at=datetime.fromisoformat(entry['processed_at']),
    )
