from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from automate.eserv.types import (
        EmailInfo,
        ErrorDict,
        PipelineError,
        ProcessedResult,
        ProcessedResultDict,
    )


@overload
def result_factory(
    *,
    record: EmailInfo | None,
    error: PipelineError | ErrorDict | None = None,
) -> ProcessedResult: ...
@overload
def result_factory(entry: ProcessedResultDict, /) -> ProcessedResult: ...
def result_factory(
    entry: ProcessedResultDict | None = None,
    *,
    record: EmailInfo | None = None,
    error: PipelineError | ErrorDict | None = None,
) -> ProcessedResult:
    """Create a ProcessedResult instance."""
    from automate.eserv.record import record_factory
    from automate.eserv.types import ProcessedResult

    if entry is not None:
        return ProcessedResult(
            record=record_factory(
                uid=entry['uid'],
                sender=entry['sender'],
                subject=entry['subject'],
            ),
            error=entry['error'],
            processed_at=datetime.fromisoformat(entry['processed_at']),
        )

    if isinstance(error, Exception):
        error = error.entry()

    return ProcessedResult(record=record, error=error)
