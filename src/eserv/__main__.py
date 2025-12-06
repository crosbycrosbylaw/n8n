# pyright: reportMissingTypeStubs = false, reportUnknownMemberType = false

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import fire

from eserv.core import pipeline_factory
from eserv.record import record_factory

if TYPE_CHECKING:
    from eserv.types import ProcessedResult


if __name__ == '__main__':
    pipeline = pipeline_factory()

    class _component:
        @staticmethod
        def process(string: str, **kwds: Any) -> ProcessedResult:
            return pipeline.execute(record_factory(f'{string}', **kwds))

        monitor = staticmethod(pipeline.monitor)

    fire.Fire(_component)
