"""PDF text extraction utilities using PyMuPDF (fitz).

Provides functions for extracting text from PDF files and document stores.
Handles multi-page PDFs and returns concatenated text.

Functions:
    extract_text_from_pdf: Extract text from a single PDF file.
    extract_text_from_store: Extract text from all PDFs in a document store.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pymupdf as fitz
from rampy import create_field_factory

from setup_console import console

if TYPE_CHECKING:
    from pathlib import Path


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file.

    Args:
        pdf_path: Path to PDF file.

    Returns:
        Concatenated text from all pages.

    Raises:
        FileNotFoundError: If PDF file doesn't exist.

    """
    if not pdf_path.exists():
        message = f'PDF file not found: {pdf_path}'
        raise FileNotFoundError(message)

    subcons = console.bind(path=pdf_path.as_posix())

    try:
        doc = fitz.open(pdf_path)
        text_parts: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(page.get_text())

        doc.close()

        full_text = '\n'.join(text_parts)
        subcons.info('Extracted text from PDF', pages=len(text_parts), chars=len(full_text))

    except Exception:
        subcons.exception('PDF text extraction')
        raise

    else:
        return full_text


def _extract_text_from_store(store_path: Path) -> dict[str, str]:
    """Extract text from all PDFs in a document store directory.

    Args:
        store_path: Path to document store directory.

    Returns:
        Dictionary mapping PDF filenames to extracted text.

    Raises:
        ValueError:
            If the document storage path is invalid.

    """
    if not store_path.exists() or not store_path.is_dir():
        message = f'Invalid document store path: {store_path}'
        raise ValueError(message)

    subcons = console.bind(store_path=store_path.as_posix())

    if not (pdf_files := [*store_path.glob('*.pdf')]):
        subcons.warning('No PDF files found in store')
        return {}

    extracted: dict[str, str] = {}

    for f in pdf_files:
        try:
            text = _extract_text_from_pdf(f)
            extracted[f.name] = text
        except Exception:
            console.exception(
                event='PDF text extraction',
                store_path=store_path.as_posix(),
                pdf_path=f.as_posix(),
            )

            extracted[f.name] = ''

    subcons.info(
        event='Extracted text from store',
        pdf_count=len(pdf_files),
        success_count=sum(1 for t in extracted.values() if t),
    )

    return extracted


@dataclass
class TextExtractor:
    path: Path

    def get_text(self, override: Path | None = None) -> str:
        """Extract text content from a PDF file at the specified path.

        Returns:
            Extracted text from the PDF file as a string

        Raises:
            FileNotFoundError:
                If the provided path is missing or is not a file.

        """
        path = (override or self.path).resolve(strict=True)

        if path.is_file():
            return _extract_text_from_pdf(path)

        raise FileNotFoundError(path)

    def collect_text(self, override: Path | None = None) -> dict[str, str]:
        """Extract text content from all PDF files contained in the specified path.

        If the path points to a file, the returned dictionary will have extract texts \
            from any PDF files within the same directory.

        Returns:
            A mapping of filenames to their text content.

        Raises:
            FileNotFoundError:
                If the provided path does not exist.

        """
        path = (override or self.path).resolve(strict=True)

        if path.is_dir():
            return _extract_text_from_store(path)

        if path.is_file():
            return _extract_text_from_store(path.parent)

        raise FileNotFoundError(path)

    def extract_names(self, override: Path | None = None) -> list[str]:
        path = (override or self.path).resolve(strict=True)

        if path.is_dir():
            out: list[str] = []

            for p in path.iterdir():
                if p.is_file():
                    out.extend(self.extract_names(p))

            return out

        text = self.get_text(path)

        # Patterns for case name extraction
        patterns = [
            re.compile(r'Case\s+Name:?\s+(.+?)(?:\n|$)', re.IGNORECASE),
            re.compile(r'Re:?\s+(.+?)(?:\n|$)', re.IGNORECASE),
            re.compile(r'Matter:?\s+(.+?)(?:\n|$)', re.IGNORECASE),
            re.compile(r'In\s+re:?\s+(.+?)(?:\n|$)', re.IGNORECASE),
        ]

        case_names: list[str] = []
        for pattern in patterns:
            matches = pattern.findall(text)
            case_names.extend(matches)

        # Clean and deduplicate
        cleaned = [' '.join(name.split()) for name in case_names]
        unique = [*dict.fromkeys(cleaned)]  # Preserve order while deduplicating

        console.info(event='Extracted case names from PDF', path=path.as_posix(), count=len(unique))

        return unique


text_extractor_factory = create_field_factory(TextExtractor)
