from __future__ import annotations

import contextlib
import typing
from datetime import UTC, datetime, timedelta

if typing.TYPE_CHECKING:
    from pathlib import Path

from rampy import rootpath

# -- Temporary Files -- #

TMP = rootpath('service', 'tmp', mkdir=True)

prune_interval: timedelta = timedelta(hours=6)
pruned_at: datetime = datetime.now(UTC) - prune_interval


def _prune_temp() -> None:
    for p in TMP.iterdir():
        if p.is_dir() and not [*p.iterdir()]:
            with contextlib.suppress(PermissionError):
                p.unlink()

    global pruned_at  # noqa: PLW0603

    pruned_at = datetime.now(UTC)


def _clean_document_name(raw: str | None) -> str:
    prefix = '' if not raw else f'{raw}_'
    return ''.join(c for c in f'{prefix}temp_store' if c.isalnum() or c in {'.', '_', '-'})


def document_store_factory(name: str | None = None) -> Path:
    """Get a temporary directory to store downloaded documents."""
    if (datetime.now(UTC) - prune_interval) > pruned_at:
        _prune_temp()

    cleaned = _clean_document_name(name)

    path = TMP / cleaned
    path.mkdir(parents=True, exist_ok=True)

    return path.resolve(strict=True)
