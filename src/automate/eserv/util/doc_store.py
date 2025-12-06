from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from pathlib import Path

from rampy import rootpath

# -- Temporary Files -- #

TMP = rootpath('service', 'tmp', mkdir=True)


def _clean_document_name(raw: str | None) -> str:
    prefix = '' if not raw else f'{raw}_'
    return ''.join(c for c in f'{prefix}temp_store' if c.isalnum() or c in {'.', '_', '-'})


def document_store_factory(name: str | None = None) -> Path:
    """Get a temporary directory to store downloaded documents."""
    cleaned = _clean_document_name(name)

    path = TMP / cleaned
    path.mkdir(parents=True, exist_ok=True)

    return path.resolve(strict=True)


def clear_temp() -> None:
    import shutil

    shutil.rmtree(TMP, ignore_errors=True)
