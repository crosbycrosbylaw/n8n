from __future__ import annotations

import functools
import re
import unicodedata
from typing import Iterable, TypedDict

from rampy import json

from .temp import TMP

_METADATA_PATH = TMP / "metadata.json"


class _DocumentMetadata(TypedDict):
    processed: bool
    document: dict[str, str]
    response: dict[str, str | dict[str, str]]


class MetadataDict(TypedDict):
    updated: float | None
    desc: str | None
    docs: list[_DocumentMetadata]


def _read_metadata():
    try:
        data = _METADATA_PATH.read_bytes()
        return MetadataJSON.loads(data)
    except FileNotFoundError:
        pass
    except Exception as err:
        print(err)

    return MetadataJSON()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def _split_case_name(case_name: str | None) -> Iterable[str]:
    if not case_name:
        return []

    yields: list[str] = []
    yields.append(case_name)

    parts = re.split(r"\s+v(?:s\.?)?\s+", case_name, maxsplit=1, flags=re.I)
    if len(parts) == 2:
        left, right = (p.strip() for p in parts)
        if left:
            yields.append(left)
        if right:
            yields.append(right)
        yields.append(f"{left} v {right}".strip())

    return yields


class MetadataView:
    def __init__(self, store: json[str, DocumentInfo]):
        self.store = store
        self._alias_map: dict[str, list[tuple[str, DocumentInfo]]] = {}
        self._doc_aliases: dict[int, list[str]] = {}
        self._path_map: dict[str, list[DocumentInfo]] = {}
        self._filename_map: dict[str, list[DocumentInfo]] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        for key, doc in self.store.items():
            aliases: set[str] = {key}

            if href := doc.href:
                aliases.add(href)

            if name := doc.name:
                self._filename_map.setdefault(name.lower(), []).append(doc)
                aliases.add(name)

            [aliases.add(p) for p in _split_case_name(doc.desc) if p]

            def update_path_map(strpath: str):
                self._path_map.setdefault(strpath.lower(), []).append(doc)
                aliases.add(strpath)

            [update_path_map(s) for f in ["path", "path_display"] if (s := getattr(doc, f, ""))]

            normalized = []
            for a in aliases:
                if norm := _normalize(a):
                    self._alias_map.setdefault(norm, []).append((a, doc))
                    normalized.append(a)

            if normalized:
                self._doc_aliases[id(doc)] = normalized

    def lookup(self, value: str) -> list[DocumentInfo]:
        norm = _normalize(value)
        return [doc for _, doc in self._alias_map.get(norm, [])]

    def aliases_for(self, doc: DocumentInfo) -> list[str]:
        return self._doc_aliases.get(id(doc), [])

    def for_path(self, value: str) -> list[DocumentInfo]:
        return self._path_map.get(value.lower(), []) if value else []

    def for_filename(self, value: str) -> list[DocumentInfo]:
        return self._filename_map.get(value.lower(), []) if value else []

    def items(self):
        return self.store.items()


@functools.lru_cache(maxsize=1)
def _get_view() -> MetadataView:
    return MetadataView(_read_metadata())


def get_metadata_view() -> MetadataView:
    return _get_view()


def refresh_metadata_cache() -> None:
    _get_view.cache_clear()


__all__ = [
    "MetadataView",
    "get_metadata_view",
    "refresh_metadata_cache",
]
