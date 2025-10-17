from __future__ import annotations

from dataclasses import field
from typing import Generator, Iterator, Sequence, TypedDict

from common import Runner
from rampy import root
from rampy.json import JSON
from rapidfuzz.process import extract


class ExtractionMapping(TypedDict):
    name: str
    pathLower: str
    pathDisplay: str


class IndexEntry(ExtractionMapping):
    id: str
    type: str


def initialize_iterator() -> Iterator[IndexEntry]:
    dbx_index = root.join("service", "dbx_index.json", resolve=True)
    index_json = JSON[list[IndexEntry]].loads(f'{{ "entries": "{dbx_index.read_text()}" }}')
    return iter(index_json["entries"])


class FolderFinder(Runner):
    query: Sequence[str] = field(init=False)

    _iterator: Iterator[IndexEntry] = field(init=False, default_factory=initialize_iterator)

    def iter_choices(self) -> Generator[ExtractionMapping]:
        try:
            while True:
                yield ExtractionMapping(next(self._iterator))
        except StopIteration:
            pass

    def setup(self) -> None:
        self.query = [x for x in self.input[1:] if x]

    def run(self) -> None:
        for choices in self.iter_choices():
            results = extract(self.query, choices=choices, limit=3)
            for choice, score, distance in results:
                ...
