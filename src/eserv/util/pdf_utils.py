"""PDF text extraction utilities using PyMuPDF (fitz).

Provides functions for extracting text from PDF files and document stores.
Handles multi-page PDFs and returns concatenated text.

Functions:
    extract_text_from_pdf: Extract text from a single PDF file.
    extract_text_from_store: Extract text from all PDFs in a document store.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pymupdf as fitz
from rampy import console

if TYPE_CHECKING:
    from pathlib import Path


def extract_text_from_pdf(pdf_path: Path) -> str:
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

    cons = console.bind(path=pdf_path.as_posix())

    try:
        doc = fitz.open(pdf_path)
        text_parts: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(page.get_text())  # type: ignore[membertype]

        doc.close()

        full_text = '\n'.join(text_parts)
        cons.info('Extracted text from PDF', pages=len(text_parts), chars=len(full_text))

    except:
        cons.exception('Failed to extract PDF text')
        raise

    else:
        return full_text


def extract_text_from_store(store_path: Path) -> dict[str, str]:
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

    cons = console.bind(store_path=store_path.as_posix())

    if not (pdf_files := [*store_path.glob('*.pdf')]):
        cons.warning('No PDF files found in store')
        return {}

    extracted: dict[str, str] = {}

    for f in pdf_files:
        try:
            text = extract_text_from_pdf(f)
            extracted[f.name] = text
        except Exception:
            cons.exception('Failed to extract PDF in store', pdf_path=f.as_posix())
            extracted[f.name] = ''

    successful: int = sum(1 for t in extracted.values() if t)

    cons.info('Extracted text from store', pdf_count=len(pdf_files), success_count=successful)

    return extracted
