from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from eserv.monitor.types import EmailInfo, ErrorDict, ProcessedResultDict, ProcessStatus


@dataclass(slots=True)
class ProcessedResult:
    """Result of processing a single email."""

    record: EmailInfo
    error: ErrorDict | None

    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def status(self) -> ProcessStatus:
        """Return the processing status based on error state."""
        return 'success' if self.error is None else 'error'

    def asdict(self) -> ProcessedResultDict:
        """Convert the ProcessedResult instance to a dictionary.

        Returns:
            A dictionary representation of the processed result.

        """
        return {
            'status': self.status,
            'uid': self.record.uid,
            'sender': self.record.sender,
            'subject': self.record.subject,
            'processed_at': self.processed_at.isoformat(),
            'error': self.error,
        }


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
