from __future__ import annotations

__all__ = [
    'BatchResult',
    'EmailInfo',
    'EmailProcessor',
    'EmailRecord',
    'GraphClient',
    'ProcessedResult',
]
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, NewType, NotRequired, ReadOnly, Required, TypedDict

from eserv.monitor.client import GraphClient
from eserv.monitor.processor import EmailProcessor

StatusFlag = NewType('StatusFlag', dict[Literal['id', 'value'], str])

if TYPE_CHECKING:
    __all__ += ['ErrorDict', 'ProcessStatus', 'ProcessedResultDict']

    type ProcessStatus = Literal['success', 'error']

    from typing import type_check_only

    @type_check_only
    class ErrorDict(TypedDict):
        """Typed-dict for error information.

        Attributes:
            category: The error category. Defaults to `unknown` if unspecified.
            message: The error message, if any.

        """

        category: Required[str]
        message: NotRequired[str | None]

    @type_check_only
    class ProcessedResultDict(TypedDict):
        """Typed-dict for the keyword arguments used in email-state record creation."""

        status: ReadOnly[ProcessStatus]
        error: ReadOnly[ErrorDict | None]

        uid: ReadOnly[str]
        sender: ReadOnly[str]
        subject: ReadOnly[str]

        processed_at: ReadOnly[str]


@dataclass(frozen=True, slots=True)
class EmailInfo:
    """Basic email metadata fetched from Outlook."""

    uid: str
    sender: str
    subject: str


@dataclass(frozen=True, slots=True)
class EmailRecord(EmailInfo):
    """All relevant email metadata fetched from Outlook."""

    received_at: datetime
    html_body: str


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Summary of batch processing."""

    results: Sequence[ProcessedResult]

    @property
    def total(self) -> int:
        """Return the size of the batch."""
        return len(self.results)

    @property
    def succeeded(self) -> int:
        """Return the number of successful results in this batch."""
        return len([x for x in self.results if x.status == 'success'])

    @property
    def failed(self) -> int:
        """Return the number of unsuccessful results in this batch."""
        return len([x for x in self.results if x.status == 'error'])


@dataclass(slots=True)
class ProcessedResult:
    """Result of processing a single email."""

    record: EmailInfo
    error: ErrorDict | None

    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: Literal['success', 'error'] = field(init=False)

    def __post_init__(self) -> None:
        """Set the processing status based on error state."""
        self.status = 'success' if self.error is None else 'error'

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
