from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from pathlib import Path

from rampy import root

# -- Temporary Files -- #

TMP = root() / 'service' / 'tmp'

if not TMP.is_dir():
    TMP.mkdir(parents=True, exist_ok=True)


def get_document_store(name: str | None = None) -> Path:
    """Get a temporary directory to store downloaded documents."""
    if not name:
        count = len((*TMP.iterdir(),))
        name = f'store_{count + 1}'
    else:
        name = f'store_{name}'

    name = ''.join(c for c in name if c.isalnum() or c in {'.', '_', '-'})

    path = TMP / name
    path.mkdir()

    return path
