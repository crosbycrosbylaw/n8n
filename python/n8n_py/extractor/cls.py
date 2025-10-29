from __future__ import annotations

import typing
from dataclasses import dataclass, field

from common import Runner

from .lib import canonicalize_item, process_record
from .lib.structs import ExtractionResult

if typing.TYPE_CHECKING:
    from .lib.structs import NormalizedRecord


@dataclass
class NameExtractor(Runner[list[ExtractionResult]]):
    normalized: list[NormalizedRecord] = field(init=False, default_factory=list)

    def setup(self):
        self.normalized = [canonicalize_item(i) for i in self.input]
        return super().setup()

    def run(self):
        self.json["results"] = [process_record(r) for r in self.normalized]
        return super().run()
