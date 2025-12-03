# pyright: reportMissingTypeStubs = false, reportUnknownMemberType = false

from __future__ import annotations

from typing import TYPE_CHECKING

import fire

from eserv.core import record_processor
from eserv.record import record_factory

if TYPE_CHECKING:
    from eserv.types import ProcessedResult


if __name__ == '__main__':
    processor = record_processor()

    class _component:  # noqa: N801
        @staticmethod
        def process(string: str) -> ProcessedResult:
            return processor.execute(record_factory(f'{string}'))

        monitor = staticmethod(processor.monitor)

    fire.Fire(_component)
