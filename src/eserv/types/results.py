from __future__ import annotations

__all__ = ['BatchResult', 'ProcessedResult', 'UploadResult']

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Literal

    from eserv.types import CaseMatch
    from eserv.types.enums import UploadStatus
    from eserv.types.structs import EmailInfo
    from eserv.types.typechecking import ErrorDict, ProcessedResultDict


@dataclass(slots=True, frozen=True)
class UploadResult:
    """Result of a document upload operation.

    Attributes:
        status: Upload status (success, manual_review, or error).
        folder_path: Dropbox folder path (or manual review folder).
        uploaded_files: List of uploaded file paths.
        match: Case match details if applicable.
        error: Error message if status is ERROR.

    """

    status: UploadStatus
    folder_path: str = ''
    uploaded_files: list[str] = field(default_factory=list)
    match: CaseMatch | None = None
    error: str | None = None

    @property
    def error_msg(self) -> str:
        """Get the error message.

        Returns:
            The error message, or 'unknown upload error' if no error is set.

        """
        return self.error or 'unknown upload error'


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
