from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, overload

from eserv.monitor.types import ProcessedResult

if TYPE_CHECKING:
    from eserv.monitor.types import EmailInfo, ErrorDict, ProcessedResultDict


@overload
def processed_result(record: EmailInfo, /, *, error: ErrorDict | None) -> ProcessedResult: ...
@overload
def processed_result(entry: ProcessedResultDict, /) -> ProcessedResult: ...
def processed_result(
    arg: EmailInfo | ProcessedResultDict,
    /,
    **kwds: ErrorDict | None,
) -> ProcessedResult:
    """Create a ProcessedResult instance."""
    from eserv.monitor.types import EmailInfo  # noqa: PLC0415

    if isinstance(arg, EmailInfo):
        return ProcessedResult(record=arg, error=kwds['error'])

    return ProcessedResult(
        record=EmailInfo(
            uid=arg['uid'],
            sender=arg['sender'],
            subject=arg['subject'],
        ),
        error=arg['error'],
        processed_at=datetime.fromisoformat(arg['processed_at']),
    )
