from __future__ import annotations

import typing
from dataclasses import dataclass, field

from common import Runner, get_metadata_view
from common.parsehtml import DocumentInfo

from .lib import canonicalize_item, process_record
from .lib.structs import ExtractionResult

if typing.TYPE_CHECKING:
    from .lib.structs import NormalizedRecord


@dataclass
class NameExtractor(Runner[list[ExtractionResult]]):
    normalized: list[NormalizedRecord] = field(init=False, default_factory=list)
    metadata_docs: list[DocumentInfo | None] = field(init=False, default_factory=list)

    def setup(self):
        self.normalized = [canonicalize_item(i) for i in self.input]
        metadata_view = get_metadata_view()
        self.metadata_docs.clear()

        for idx, record in enumerate(self.normalized):
            meta_doc: DocumentInfo | None = None
            original = self.input[idx] if idx < len(self.input) else None
            candidates = [original, record.get("original_source"), record.get("cleaned_text")]
            for candidate in candidates:
                if not candidate:
                    continue
                docs = metadata_view.lookup(str(candidate))
                if docs:
                    meta_doc = docs[0]
                    break
            if not meta_doc and record.get("original_source"):
                docs = metadata_view.for_path(str(record["original_source"]))
                if docs:
                    meta_doc = docs[0]

            self.metadata_docs.append(meta_doc)

            if meta_doc and "metadata" not in record["hints"]:
                record["hints"].append("metadata")
        return super().setup()

    def run(self):
        results: list[ExtractionResult] = []

        for idx, record in enumerate(self.normalized):
            result = process_record(record)
            meta_doc = self.metadata_docs[idx] if idx < len(self.metadata_docs) else None
            if not result["found_names"] and meta_doc and meta_doc.get("case_name"):
                original_cleaned = record["cleaned_text"]
                try:
                    record["cleaned_text"] = str(meta_doc["case_name"])
                    result = process_record(record)
                finally:
                    record["cleaned_text"] = original_cleaned
            results.append(result)

        self.json["results"] = results
        return super().run()
