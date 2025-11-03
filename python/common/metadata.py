from __future__ import annotations

import functools
import re
import unicodedata
from typing import Iterable

from rampy import json

from .parsehtml import DocumentInfo
from .temp import TMP

_METADATA_PATH = TMP / "metadata.json"

MetadataJSON = json[str, DocumentInfo]


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


def _split_case_name(case_name: str) -> Iterable[str]:
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
            aliases = set[str]()
            aliases.add(str(key))

            for field in ("filename", "case_name", "filed_by"):
                value = doc.get(field)
                if value:
                    aliases.add(str(value))

            aliases.update(doc.get("hrefs", []) or [])

            for part in _split_case_name(doc.get("case_name", "")):
                if part:
                    aliases.add(part)

            path_value = doc.get("path")
            if path_value:
                self._path_map.setdefault(str(path_value).lower(), []).append(doc)
                aliases.add(str(path_value))

            path_display = doc.get("path_display")
            if path_display:
                self._path_map.setdefault(str(path_display).lower(), []).append(doc)
                aliases.add(str(path_display))

            filename = doc.get("filename")
            if filename:
                self._filename_map.setdefault(str(filename).lower(), []).append(doc)

            alias_list = []
            for alias in aliases:
                norm = _normalize(alias)
                if not norm:
                    continue
                self._alias_map.setdefault(norm, []).append((alias, doc))
                alias_list.append(alias)

            if alias_list:
                self._doc_aliases[id(doc)] = alias_list

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
