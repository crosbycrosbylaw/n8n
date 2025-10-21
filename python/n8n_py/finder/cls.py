import re
import unicodedata
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Sequence, TypedDict

from common import Runner
from rampy import js, root
from rapidfuzz import fuzz, process


class IndexEntry(TypedDict):
    pathDisplay: str


class FinderMatch(IndexEntry):
    score: int
    reason: str
    matched_label: str | None


class FinderResult(TypedDict):
    query: str
    normalized_query: str
    matches: list[FinderMatch]


@dataclass
class FolderFinder(Runner[list[FinderResult]]):
    """Load dbx_index.json, build normalized index, and fuzzy-match queries to folder entries."""

    dbx_path: Path = field(init=False)
    query: Sequence[str] = field(init=False)

    index: list[IndexEntry] = field(init=False, default_factory=list)
    norm_map: dict[str, list[IndexEntry]] = field(init=False, default_factory=dict)
    choices: list[str] = field(init=False, default_factory=list)

    def setup(self):
        self.query = [str(x).strip() for x in self.input if x]

        # locate dbx_index.json managed by n8n
        self.dbx_path = root() / "service" / "dbx_index.json"
        try:
            text = Path(self.dbx_path).read_text(encoding="utf-8")
            entries = js.array[js.object[str]].loads(text)
        except JSONDecodeError as exc:
            # if unreadable, record and bail gracefully
            self.json["results"] = []
            self.warnings.append(f"could not load dbx_index.json: {exc}")
            self.index = []
            return self

        # Build index entries and normalized mapping
        for obj in entries:
            path = obj.get("pathDisplay")
            if not path:
                continue
            entry: IndexEntry = {"pathDisplay": path}
            self.index.append(entry)

            # derive candidate labels from path components (skip root like 'Clio')
            parts = [p for p in path.strip("/").split("/") if p]
            labels = []
            # take all non-numeric parts beyond the first
            for part in parts[1:]:
                # strip folder index prefixes like '00003-'
                pclean = re.sub(r"^\d+\-", "", part).strip()
                # skip small numeric-only parts
                if not re.search(r"[A-Za-z]", pclean):
                    continue
                labels.append(pclean)

            # also add last meaningful part if no labels found
            if not labels and parts:
                labels = [parts[-1]]

            for lab in labels:
                norm = self._normalize(lab)
                self.norm_map.setdefault(norm, []).append(entry)

        # build choices list for fuzzy search (unique normalized strings)
        self.choices = [*self.norm_map.keys()]

        return self

    def _normalize(self, s: str) -> str:
        # remove accents, lowercase, keep hyphens, collapse non-alnum to spaces
        s = str(s or "")
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.lower()
        s = re.sub(r"[^a-z0-9\-]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def run(self):
        if not self.index:
            # setup already recorded error
            return self

        results = []

        for q in self.query:
            qnorm = self._normalize(q)
            # exact lookup
            exact = self.norm_map.get(qnorm)
            matches: list[FinderMatch] = []
            if exact:
                for e in exact:
                    matches.append(
                        FinderMatch(
                            pathDisplay=e["pathDisplay"],
                            score=100,
                            reason="exact",
                            matched_label=None,
                        )
                    )
            else:
                # fuzzy search among normalized choices
                fuzzy = process.extract(qnorm, self.choices, scorer=fuzz.token_set_ratio, limit=5)
                for choice, score, _ in fuzzy:
                    entries = self.norm_map.get(choice, [])
                    for e in entries:
                        matches.append(
                            FinderMatch(
                                pathDisplay=e["pathDisplay"],
                                score=int(score),
                                reason="fuzzy",
                                matched_label=choice,
                            )
                        )

            # sort and dedupe by pathDisplay keeping highest score
            seen = {}
            for m in matches:
                pd = m["pathDisplay"]
                if pd not in seen or m["score"] > seen[pd]["score"]:
                    seen[pd] = m

            ranked = sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:10]
            results.append({"query": q, "normalized_query": qnorm, "matches": ranked})

        self.json["results"] = results

        return self
