import typing
from typing import Iterable, Sequence


class NormalizedRecord(typing.TypedDict):
    original_source: str | None
    is_file: bool
    raw_text: str
    cleaned_text: str
    html_detected: bool
    hints: list[str]


def new_record():
    return NormalizedRecord(
        original_source=None,
        is_file=False,
        raw_text="",
        cleaned_text="",
        html_detected=False,
        hints=[],
    )


class ExtractionResult(typing.TypedDict):
    original_source: str | None
    found_names: bool
    raw_case_text: str | None
    parties: Sequence[dict[str, Iterable]]
    pair_candidates: Sequence[dict[str, Iterable]]
