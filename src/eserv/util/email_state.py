from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, overload

import orjson

from eserv.monitor.result import processed_result

if TYPE_CHECKING:
    from pathlib import Path

    from eserv.monitor.types import EmailRecord, ErrorDict, ProcessedResultDict

# Import ProcessedResult at runtime for isinstance check
from eserv.monitor.types import ProcessedResult


@dataclass
class EmailState:
    """Audit log for processed emails (UID-based)."""

    state_file: Path
    _entries: dict[str, ProcessedResult] = field(default_factory=dict, init=False)

    @property
    def processed(self) -> set[str]:
        """Get the set of processed email UIDs."""
        return {*self._entries.keys()}

    def __post_init__(self) -> None:
        """Load email state from disk after initialization."""
        self._load()

    def _load(self) -> None:
        """Load from JSON, fresh start if missing."""
        if not self.state_file.exists():
            self._entries = {}
            return

        try:
            with self.state_file.open('rb') as f:
                data: dict[str, ProcessedResultDict] = orjson.loads(f.read())

            self._entries = {uid: processed_result(entry) for uid, entry in data.items()}
        except Exception:
            self._entries = {}

    @overload
    def record(self, result: ProcessedResult, /) -> None: ...
    @overload
    def record(self, record: EmailRecord, error: ErrorDict | None = None, /) -> None: ...
    def record(
        self,
        arg: EmailRecord | ProcessedResult,
        error: ErrorDict | None = None,
    ) -> None:
        """Record processed email."""
        if isinstance(arg, ProcessedResult):
            self._entries[arg.record.uid] = arg
        else:
            self._entries[arg.uid] = processed_result(arg, error=error)

        self._save()

    def is_processed(self, uid: str) -> bool:
        """Check if email has been processed."""
        return uid in self._entries

    def clear_flags(self, uid: str) -> None:
        """Clear flags to allow reprocessing (removes entry)."""
        self._entries.pop(uid, None)
        self._save()

    def _save(self) -> None:
        """Persist to JSON."""
        data: dict[str, ProcessedResultDict] = {
            uid: entry.asdict() for uid, entry in self._entries.items()
        }

        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with self.state_file.open('wb') as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
