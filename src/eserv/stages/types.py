from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dropbox.files import Metadata

    from eserv.types import CaseMatch

    type ResultEntries = Iterable[Metadata]
    type ResultCursor = str


class UploadStatus(Enum):
    """Upload result status."""

    SUCCESS = 'success'
    NO_WORK = 'no_work'
    MANUAL_REVIEW = 'manual_review'
    ERROR = 'error'


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
