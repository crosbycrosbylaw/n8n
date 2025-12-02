"""Pipeline error tracking and logging.

Tracks errors by pipeline stage for debugging and monitoring.
Errors are logged to JSON with timestamps and context.

Classes:
    PipelineStage: Enum of pipeline stages for error categorization.
    ErrorTracker: Error logging with stage-based categorization.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Self, Unpack

import orjson
from rampy import console

from eserv.errors._core import PipelineError

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TypedDict

    class _ErrorEntry(TypedDict):
        uid: str
        error: str
        timestamp: str
        stage: str
        context: dict[str, str]


class PipelineStage(Enum):
    """Pipeline stages for error categorization."""

    EMAIL_PARSING = 'parsing'
    DOCUMENT_DOWNLOAD = 'download'
    PDF_EXTRACTION = 'extraction'
    FOLDER_MATCHING = 'matching'
    DROPBOX_UPLOAD = 'upload'


@dataclass
class ErrorTracker:
    """Tracks pipeline errors with stage-based categorization.

    Maintains a JSON log of errors with timestamps, stages, and context.

    Attributes:
        file: Path to error log JSON file.
        _errors: In-memory error log.

    """

    file: Path
    uid: str = field(default='unknown')

    @contextmanager
    def track(self, uid: str) -> Generator[Self]:
        """Context manager to temporarily track errors for a specific email.

        Args:
            uid: Identifier for the email record to track.

        Yields:
            Self: The ErrorTracker instance with updated uid.

        """
        prev_uid = self.uid
        try:
            self.uid = uid
            yield self
        finally:
            self.uid = prev_uid

    _errors: list[_ErrorEntry] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        """Load existing error log from disk."""
        self._load_errors()

    def _load_errors(self) -> None:
        """Load error log from JSON file, creating if missing."""
        cons = console.bind(path=self.file.as_posix())

        if not self.file.exists():
            self._errors = []
            self._save_errors()

            cons.info('Created new error log file')
            return

        try:
            with self.file.open('rb') as f:
                self._errors = orjson.loads(f.read())

            cons.info('Loaded error log', error_count=len(self._errors))

        except Exception:
            cons.exception('Failed to load error log')

            self._errors = []
            self._save_errors()

    def _save_errors(self) -> None:
        """Save current error log to JSON file."""
        with self.file.open('wb') as f:
            f.write(orjson.dumps(self._errors, option=orjson.OPT_INDENT_2))

    def _save_entry(self, **entry: Unpack[_ErrorEntry]) -> None:
        self._errors.append(entry)
        self._save_errors()

    def error(
        self,
        message: str,
        stage: PipelineStage,
        context: dict[str, str] | None = None,
    ) -> PipelineError:
        """Log a pipeline error.

        Args:
            stage: Pipeline stage where error occurred.
            message: Human-readable error description.
            context: Optional additional context (e.g., file paths, API responses).

        """
        self._save_entry(
            uid=self.uid,
            error=message,
            timestamp=datetime.now(UTC).isoformat(),
            stage=stage.value,
            context=context or {},
        )

        error = PipelineError(message=message, stage=stage)
        console.bind(uid=self.uid, stage=stage.value, exc_info=error).exception()

        return error

    def exception(
        self,
        message: str,
        stage: PipelineStage,
        context: dict[str, str] | None = None,
    ) -> None:
        """Log a pipeline error.

        Args:
            stage: Pipeline stage where error occurred.
            message: Human-readable error description.
            context: Optional additional context (e.g., file paths, API responses).

        """
        self._save_entry(
            uid=self.uid,
            error=message,
            timestamp=datetime.now(UTC).isoformat(),
            stage=stage.value,
            context=context or {},
        )

        cons = console.bind(uid=self.uid, stage=stage.value)
        cons.exception(f'Pipeline error: {message}')

    def warning(
        self,
        message: str,
        stage: PipelineStage,
        context: dict[str, str] | None = None,
    ) -> None:
        """Log a pipeline error.

        Args:
            stage: Pipeline stage where error occurred.
            message: Human-readable error description.
            context: Optional additional context (e.g., file paths, API responses).

        """
        self._save_entry(
            uid=self.uid,
            error=message,
            timestamp=datetime.now(UTC).isoformat(),
            stage=stage.value,
            context=context or {},
        )

        cons = console.bind(uid=self.uid, stage=stage.value)
        cons.warning(f'Pipeline warning: {message}')

    def get_errors_for_email(self, uid: str) -> list[_ErrorEntry]:
        """Get all errors for a specific email.

        Args:
            uid: Identifier for this email record.

        Returns:
            List of error entries for this email.

        """
        return [e for e in self._errors if e['uid'] == uid]

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
