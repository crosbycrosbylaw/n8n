"""Pipeline error tracking and logging.

Tracks errors by pipeline stage for debugging and monitoring.
Errors are logged to JSON with timestamps and context.

Classes:
    PipelineStage: Enum of pipeline stages for error categorization.
    ErrorTracker: Error logging with stage-based categorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

import orjson
from rampy import console

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TypedDict

    class _ErrorEntry(TypedDict):
        timestamp: str
        email_hash: str
        error: str
        stage: str
        context: dict[str, str]


class PipelineStage(Enum):
    """Pipeline stages for error categorization."""

    EMAIL_PARSING = 'email_parsing'
    DOCUMENT_DOWNLOAD = 'document_download'
    PDF_EXTRACTION = 'pdf_extraction'
    FOLDER_MATCHING = 'folder_matching'
    DROPBOX_UPLOAD = 'dropbox_upload'


@dataclass
class ErrorTracker:
    """Tracks pipeline errors with stage-based categorization.

    Maintains a JSON log of errors with timestamps, stages, and context.

    Attributes:
        log_file: Path to error log JSON file.
        _errors: In-memory error log.

    """

    log_file: Path
    _errors: list[_ErrorEntry] = field(default_factory=list[Any], init=False)

    def __post_init__(self) -> None:
        """Load existing error log from disk."""
        self._load_errors()

    def _load_errors(self) -> None:
        """Load error log from JSON file, creating if missing."""
        cons = console.bind(path=self.log_file.as_posix())

        if not self.log_file.exists():
            self._errors = []
            self._save_errors()

            cons.info('Created new error log file')
            return

        try:
            with self.log_file.open('rb') as f:
                self._errors = orjson.loads(f.read())

            cons.info('Loaded error log', error_count=len(self._errors))

        except Exception:
            cons.exception('Failed to load error log')

            self._errors = []
            self._save_errors()

    def _save_errors(self) -> None:
        """Save current error log to JSON file."""
        with self.log_file.open('wb') as f:
            f.write(orjson.dumps(self._errors, option=orjson.OPT_INDENT_2))

    def log_error(
        self,
        email_hash: str,
        stage: PipelineStage,
        error_message: str,
        context: dict[str, str] | None = None,
    ) -> None:
        """Log a pipeline error.

        Args:
            email_hash: Hash of email subject for correlation.
            stage: Pipeline stage where error occurred.
            error_message: Human-readable error description.
            context: Optional additional context (e.g., file paths, API responses).

        """
        error_entry: _ErrorEntry = {
            'timestamp': datetime.now(UTC).isoformat(),
            'email_hash': email_hash,
            'stage': stage.value,
            'error': error_message,
            'context': context or {},
        }

        self._errors.append(error_entry)
        self._save_errors()

        cons = console.bind(email_hash=email_hash, stage=stage.value, message=error_message)
        cons.error('Pipeline error logged')

    def get_errors_for_email(self, email_hash: str) -> list[_ErrorEntry]:
        """Get all errors for a specific email.

        Args:
            email_hash: Hash of email subject.

        Returns:
            List of error entries for this email.

        """
        return [e for e in self._errors if e['email_hash'] == email_hash]

    def get_errors_by_stage(self, stage: PipelineStage) -> list[_ErrorEntry]:
        """Get all errors for a specific pipeline stage.

        Args:
            stage: Pipeline stage to filter by.

        Returns:
            List of error entries for this stage.

        """
        return [e for e in self._errors if e['stage'] == stage.value]

    def clear_old_errors(self, days: int = 30) -> None:
        """Remove errors older than specified days.

        Args:
            days: Number of days to retain errors.

        """
        cutoff = datetime.now(UTC).timestamp() - (days * 86400)

        self._errors = [
            e for e in self._errors if datetime.fromisoformat(e['timestamp']).timestamp() > cutoff
        ]
        self._save_errors()

        console.bind(cutoff_days=days).info('Cleared old errors')
