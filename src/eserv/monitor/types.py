from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime
    from typing import NotRequired, ReadOnly, Required, TypedDict

    from eserv.monitor.result import ProcessedResult

    type ProcessStatus = Literal['success', 'error']

    class ErrorDict(TypedDict):
        """Typed-dict for error information.

        Attributes:
            category: The error category. Defaults to `unknown` if unspecified.
            message: The error message, if any.

        """

        category: Required[str]
        message: NotRequired[str | None]

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

    total: int
    succeeded: int
    failed: int
    results: list[ProcessedResult]
