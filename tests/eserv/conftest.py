from __future__ import annotations

import typing

import pytest
from pytest_fixture_classes import fixture_class
from rampy import test

from tests.eserv.lib import SAMPLE_EMAIL

if typing.TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence
    from pathlib import Path

    from eserv.types import EmailRecord


@pytest.fixture
def tempdir() -> Generator[Path]:
    path = test.directory('pytest_temp')
    try:
        yield path
    finally:
        path.clean()


@pytest.fixture
def record() -> EmailRecord:
    from eserv.record import record_factory

    return record_factory(SAMPLE_EMAIL)


@fixture_class(name='setup_files')
class SetupFilesFixture:
    tempdir: Path

    def __call__(self, registry: Mapping[str, bytes]) -> Sequence[Path]:
        out: list[Path] = []

        for name, content in registry.items():
            path = self.tempdir / name
            path.write_bytes(content)

            out.append(path)

        return out
