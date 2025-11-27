"""Email processing state tracking with weekly rotation and archival.

Tracks which emails have been processed to prevent duplicate processing.
Automatically rotates state weekly and archives old entries.

Classes:
    EmailState: Email processing state manager with weekly rotation.

Functions:
    hash_email_subject: Create a deterministic hash from an email subject.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import TYPE_CHECKING, Any

import orjson
from rampy import console

if TYPE_CHECKING:
    from pathlib import Path


def hash_email_subject(subject: str) -> str:
    """Create a deterministic hash from an email subject.

    Args:
        subject: Email subject line.

    Returns:
        SHA256 hash of the subject (first 16 characters).

    """
    return hashlib.sha256(subject.encode()).hexdigest()[:16]


@dataclass
class EmailState:
    """Tracks processed emails with weekly rotation and archival.

    Maintains a JSON file with processed email hashes and their matched folders.
    Automatically rotates state weekly to prevent unbounded growth.

    Attributes:
        state_file: Path to state JSON file.
        _state: In-memory state cache.
        _week_start: Start of current week for rotation logic.

    """

    state_file: Path
    _state: dict[str, dict[str, str | None]] = field(default_factory=dict[str, Any], init=False)
    _week_start: datetime = field(default_factory=partial(datetime.now, UTC), init=False)

    def __post_init__(self) -> None:
        """Load existing state from disk."""
        self._load_state()

    def _load_state(self) -> None:
        """Load state from JSON file, creating if missing."""
        cons = console.bind(path=self.state_file.as_posix())

        if not self.state_file.exists():
            self._state = {}
            self._save_state()

            cons.info('Created new email state file')
            return

        try:
            with self.state_file.open('rb') as f:
                data = orjson.loads(f.read())
            self._state = data.get('processed', {})
            self._week_start = datetime.fromisoformat(
                data.get('week_start', datetime.now(UTC).isoformat())
            )
        except Exception:
            cons.exception('Failed to load email state')

            self._state = {}
            self._save_state()
        else:
            cons.info('Loaded email state', processed_count=len(self._state))

    def _save_state(self) -> None:
        """Save current state to JSON file."""
        data = {
            'week_start': self._week_start.isoformat(),
            'processed': self._state,
        }
        with self.state_file.open('wb') as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def _should_rotate(self) -> bool:
        """Check if weekly rotation is needed."""
        return (datetime.now(UTC) - self._week_start) > timedelta(weeks=1)

    def _rotate(self) -> None:
        """Archive current state and start fresh week."""
        if not self._state:
            return

        # Create archive file with timestamp
        archive_name = f'email_state_archive_{self._week_start.strftime("%Y%m%d")}.json'
        archive_path = self.state_file.parent / archive_name

        cons = console.bind(archive_path=archive_path.as_posix(), entries=len(self._state))

        # Save archive
        archive_data = {
            'week_start': self._week_start.isoformat(),
            'week_end': datetime.now(UTC).isoformat(),
            'processed': self._state,
        }
        with archive_path.open('wb') as f:
            f.write(orjson.dumps(archive_data, option=orjson.OPT_INDENT_2))

        cons.info('Archived email state')

        # Reset state
        self._state = {}
        self._week_start = datetime.now(UTC)
        self._save_state()

    def mark_processed(
        self, subject: str, matched_folder: str | None, timestamp: datetime | None = None
    ) -> None:
        """Mark an email as processed.

        Args:
            subject: Email subject line.
            matched_folder: Dropbox folder path matched, or None if manual review.
            timestamp: When processed (defaults to now).

        """
        cons = console.bind(subject=subject, matched_folder=matched_folder)

        if self._should_rotate():
            self._rotate()

        email_hash = hash_email_subject(subject)
        ts = timestamp or datetime.now(UTC)

        self._state[email_hash] = {
            'subject': subject,
            'matched_folder': matched_folder,
            'timestamp': ts.isoformat(),
        }
        self._save_state()

        cons.info('Marked email as processed')

    def is_processed(self, subject: str) -> bool:
        """Check if an email has been processed this week.

        Args:
            subject: Email subject line.

        Returns:
            True if already processed, False otherwise.

        """
        if self._should_rotate():
            self._rotate()

        return hash_email_subject(subject) in self._state

    def get_matched_folder(self, subject: str) -> str | None:
        """Get the matched folder for a processed email.

        Args:
            subject: Email subject line.

        Returns:
            Matched folder path, or None if not processed or manual review.

        """
        email_hash = hash_email_subject(subject)
        entry = self._state.get(email_hash)

        return entry.get('matched_folder') if entry else None
