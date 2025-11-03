from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Sequence

from common import Runner, get_metadata_view, refresh_metadata_cache
from common.metadata import MetadataView
from common.parsehtml import DocumentInfo
from n8n_py import extractor, finder, parser
from rampy import json


def _inputs_with_default(*strings: str | None) -> list[str]:
    if not strings and len(sys.argv) > 1:
        argv = sys.argv.copy()
        argv.pop(0)
        return argv
    return [x for x in strings if x]


def _unique(strings: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in strings:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _meaningful(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip()
    if not value:
        return False
    if value.lower().startswith("http"):
        return False
    return any(ch.isalpha() for ch in value)


def _lookup_doc(metadata_view: MetadataView, path: str) -> DocumentInfo | None:
    normalized = str(path)
    docs = metadata_view.for_path(normalized)
    if docs:
        return docs[0]

    filename = Path(normalized).name
    docs = metadata_view.for_filename(filename)
    if docs:
        return docs[0]

    docs = metadata_view.lookup(filename)
    return docs[0] if docs else None


def _run_parser(content: str | None) -> tuple[list[str], parser.main | None]:
    if inputs := _inputs_with_default(content):
        runner = parser.main(inputs, pipeline=True)
        paths = runner.json.get("paths", [])
        return paths, runner
    return [], None


def _run_extractor(inputs: Sequence[str] = ()) -> tuple[list[extractor.result], extractor.main | None]:
    if inputs := _inputs_with_default(*inputs):
        runner = extractor.main([*inputs], pipeline=True)
        results = runner.json.get("results", [])
        return results, runner
    return [], None


def _run_finder(queries: Sequence[str] = ()) -> tuple[list[finder.result], finder.main | None]:
    if queries := _inputs_with_default(*queries):
        runner = finder.main([*queries], pipeline=True)
        results = runner.json.get("results", [])
        return list(results), runner
    return [], None


def main(content: str | None = None) -> json[str, object]:
    parsed_paths, parser_runner = _run_parser(content)

    # ensure metadata reflects any newly saved attachments before continuing
    refresh_metadata_cache()

    metadata_view = get_metadata_view()

    if not parsed_paths:
        parsed_paths = [str(doc["path"]) for _, doc in metadata_view.items() if doc.get("path")]

    parsed_paths = _unique(parsed_paths)

    documents: list[DocumentInfo] = []
    for path in parsed_paths:
        if not path:
            continue
        if doc := _lookup_doc(metadata_view, path):
            documents.append(doc)

    extractor_inputs = [p for p in parsed_paths if Path(p).is_file()]
    extractor_results, extractor_runner = _run_extractor(extractor_inputs)

    queries: set[str] = set()
    for doc in documents:
        for candidate in (
            doc.get("case_name"),
            doc.get("filed_by"),
            doc.get("filename"),
            doc.get("path_display"),
        ):
            if _meaningful(candidate):
                queries.add(str(candidate))

        for alias in metadata_view.aliases_for(doc):
            if _meaningful(alias):
                queries.add(alias)

    for record in extractor_results:
        raw_case = record.get("raw_case_text")
        if _meaningful(raw_case):
            queries.add(str(raw_case))

        parties = record.get("parties", [])
        for party in parties:
            candidates = party.get("candidates", [])
            for candidate in candidates:
                form = candidate.get("form")
                if _meaningful(form):
                    queries.add(str(form))

    query_list = sorted(queries, key=lambda s: s.lower())
    finder_results, finder_runner = _run_finder(query_list)

    summary = json[str, object](
        paths=parsed_paths,
        documents=documents,
        extractor=extractor_results,
        queries=query_list,
        finder=finder_results,
    )

    for name in "parser", "extractor", "finder":
        if (runner := locals().get(f"{name}_runner", None)) and isinstance(runner, Runner):
            summary[f"{name}_logs"] = runner.logs
            summary[f"{name}_warnings"] = runner.warnings

    return summary


if __name__ == "__main__":  # pragma: no cover
    main()
