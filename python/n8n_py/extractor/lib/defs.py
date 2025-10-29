from __future__ import annotations

import html
import re
import unicodedata
from pathlib import Path
from typing import Any

import bs4
from nameparser import HumanName

from .const import keywords, regex
from .structs import ExtractionResult, NormalizedRecord, new_record


def canonicalize_item(item: str) -> NormalizedRecord:
    """Normalize string items into a list of canonical records.

    Each record is a typed_dict with keys:
      - original_source: str (path or inline)
      - is_file: bool
      - raw_text: str
      - cleaned_text: str (HTML stripped/unescaped, whitespace-normalized)
      - html_detected: bool
      - hints: list[str]
    """

    try:
        p = Path(item)
    except Exception:
        p = None

    record = new_record()

    if p is not None and p.exists() and p.is_file():
        record["original_source"] = str(p)
        record["is_file"] = True
        try:
            text = p.read_text(errors="replace")
        except Exception:
            text = ""
    else:
        record["original_source"] = str(item)
        text = str(item or "")

    record["raw_text"] = text

    # Heuristic: detect HTML by presence of tags or entities
    html_hint = bool(re.search(r"<\s*\w+[^>]*>", text)) or ("&lt;" in text) or ("&gt;" in text)
    record["html_detected"] = html_hint

    cleaned = text
    if html_hint:
        try:
            soup = bs4.BeautifulSoup(text, features="html.parser")
            # remove scripts/styles
            for s in soup(["script", "style"]):
                s.decompose()
            cleaned = soup.get_text(" ", strip=True)
        except Exception:
            cleaned = text

    # Unescape entities and normalize whitespace; preserve case for name parsing
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    record["cleaned_text"] = cleaned

    # Quick hints for parser
    low = cleaned.lower()
    if re.search(r"\b(vs?\.?|v\b)\b", cleaned, flags=re.I):
        record["hints"].append("has_vs")
    if re.search(r"case style|in the matter of|envelope number|case number", low):
        record["hints"].append("has_case")
    if "confidential" in low or "redacted" in low:
        record["hints"].append("confidential")

    return record


def is_corporate(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    if any(re.search(r"\b" + re.escape(tok) + r"\b", low) for tok in keywords.corporate):
        return True
    words = [w for w in re.split(r"\s+", text) if w]
    # very long multiword uppercase tends to be orgs
    if len(words) > 1 and sum(1 for c in text if c.isupper()) / max(1, len(text)) > 0.6:
        return True
    # single-token all-caps like 'IBM' is also org
    if len(words) == 1 and words[0].isupper() and len(words[0]) > 1:
        return True
    return False


def normalize_for_nameparsing(text: str) -> str:
    t = text.strip()
    # remove extraneous punctuation around name
    t = re.sub(r"^[\s\-\:\.\,\(\)]+|[\s\-\:\.\,\(\)]+$", "", t)
    # If text is ALL CAPS and not corporate, title-case it for nameparser
    if not is_corporate(t) and t.upper() == t and any(c.isalpha() for c in t):
        t = t.title()
    return t


def normalize_for_index(s: str) -> str:
    # remove accents, lowercase, keep hyphens and letters/numbers, collapse spaces
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    # replace anything not alnum or hyphen with space
    s = re.sub(r"[^a-z0-9\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def generate_name_candidates(parsed: HumanName, raw: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    first = (parsed.first or "").strip()
    last = (parsed.last or "").strip()
    middle = (parsed.middle or "").strip()

    if first and last:
        form = f"{first} {last}".strip()
        norm = normalize_for_index(form)
        candidates.append({"form": form, "first": first, "last": last, "score": 100, "normalized": norm})
        # reversed
        form2 = f"{last}, {first}".strip()
        norm2 = normalize_for_index(f"{first} {last}")
        candidates.append({"form": form2, "first": first, "last": last, "score": 95, "normalized": norm2})
        # with middle initial
        if middle:
            mi = middle.split()[0]
            fm = f"{first} {mi} {last}"
            candidates.append({
                "form": fm,
                "first": first,
                "last": last,
                "score": 90,
                "normalized": normalize_for_index(fm),
            })
            fm2 = f"{first} {mi[0]}. {last}".strip()
            candidates.append({
                "form": fm2,
                "first": first,
                "last": last,
                "score": 88,
                "normalized": normalize_for_index(fm2),
            })
    else:
        # fallback: use raw as a soft candidate
        candidates.append({"form": raw, "score": 60, "normalized": normalize_for_index(raw)})

    return candidates


def parse_party(text: str) -> dict[str, Any]:
    entry: dict[str, Any] = {"raw": text, "type": "person", "candidates": []}
    if not text:
        return entry

    if is_corporate(text):
        entry["type"] = "company"
        entry["candidates"].append({"form": text.strip(), "score": 100})
        return entry

    norm = normalize_for_nameparsing(text)

    # Prefer nameparser but fall back gracefully
    try:
        hn = HumanName(norm)
        # If nameparser produced no last name but text contains a comma, try invert
        if not hn.last and "," in text:
            parts = [p.strip() for p in text.split(",") if p.strip()]
            if len(parts) >= 2:
                # assume 'Last, First Middle'
                hn = HumanName(f"{parts[1]} {parts[0]}")

        candidates = generate_name_candidates(hn, text)
    except Exception:
        candidates = [{"form": text, "score": 50}]

    # dedupe by normalized lower form
    seen = set()
    deduped: list[dict[str, Any]] = []
    for c in candidates:
        key = c.get("normalized") or c.get("form", "")
        key = str(key).lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    entry["candidates"] = deduped
    # canonical first/last for easier finder matching
    if deduped and isinstance(deduped[0].get("first"), str):
        entry["canonical_first"] = (deduped[0].get("first") or "").lower() or None
        entry["canonical_last"] = (deduped[0].get("last") or "").lower() or None
    else:
        entry["canonical_first"] = None
        entry["canonical_last"] = None

    return entry


def extract_v_style(cleaned: str):
    # prefer the first long-ish match that looks like two name-like sides
    m = regex.vs.search(cleaned)
    if m:
        left = m.group("left").strip()
        right = m.group("right").strip()
        return left, right, m.group("sep")

    # try case-hint block
    m2 = regex.hint.search(cleaned)
    if m2:
        block = m2.group(1).strip()
        m3 = regex.vs.search(block)
        if m3:
            return m3.group("left").strip(), m3.group("right").strip(), m3.group("sep")
        # otherwise try splitting on known delimiters
        parts = [p.strip() for p in re.split(r";|\n|\||\\/", block) if p.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1], None

    # scan lines for a v/versus
    for line in cleaned.splitlines():
        if re.search(r"\b(vs?\.?|v\b)\b", line, flags=re.I):
            m4 = regex.vs.search(line)
            if m4:
                return m4.group("left").strip(), m4.group("right").strip(), m4.group("sep")

    # fallback: try ' and ' when it looks like two names
    for sep in [" and ", " & "]:
        if sep in cleaned.lower():
            parts = [p.strip() for p in re.split(re.escape(sep), cleaned, maxsplit=1) if p.strip()]
            if len(parts) == 2 and 2 <= len(parts[0].split()) <= 5 and 2 <= len(parts[1].split()) <= 5:
                return parts[0], parts[1], sep.strip()

    return None, None, None


def process_record(record: NormalizedRecord):
    cleaned = record["cleaned_text"]
    left, right, sep = extract_v_style(cleaned)
    parties: list[dict[str, Any]] = []
    pair_candidates: list[dict[str, Any]] = []
    raw_case = None

    if left and right:
        raw_case = f"{left} {sep or 'vs'} {right}"
        left_entry = parse_party(left)
        right_entry = parse_party(right)
        parties = [left_entry, right_entry]

        # create top pair candidates from top candidate of each side
        if left_entry["candidates"] and right_entry["candidates"]:
            for left_cand in left_entry["candidates"][:3]:
                for right_cand in right_entry["candidates"][:3]:
                    pair_candidates.append({
                        "left": left_cand["form"],
                        "right": right_cand["form"],
                        "score": left_cand.get("score", 0) + right_cand.get("score", 0),
                    })

    return ExtractionResult(
        original_source=record.get("original_source"),
        found_names=bool(parties),
        raw_case_text=raw_case,
        parties=parties,
        pair_candidates=pair_candidates,
    )
