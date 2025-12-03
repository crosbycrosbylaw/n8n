from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from pathlib import Path

from rampy import rootpath

# -- Temporary Files -- #

TMP = rootpath('service', 'tmp', mkdir=True)


def _clean_document_name(raw: str | None) -> str:
    if not raw:
        count = len((*TMP.iterdir(),))
        name = f'store_{count + 1}'
    else:
        name = f'store_{raw}'

    return ''.join(c for c in name if c.isalnum() or c in {'.', '_', '-'})


def document_store(name: str | None = None) -> Path:
    """Get a temporary directory to store downloaded documents."""
    cleaned = _clean_document_name(name)

    path = TMP / cleaned
    path.mkdir(parents=True)

    return path.resolve(strict=True)
