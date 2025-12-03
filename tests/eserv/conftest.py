from __future__ import annotations

import typing

import pytest
from rampy import test

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path


@pytest.fixture
def _generator(dirname: str) -> Generator[Path]:
    path = test.directory('eserv', dirname)
    try:
        yield path
    finally:
        path.clean()


@pytest.fixture
def tempdir() -> Callable[[str], Path]:
    return _generator
