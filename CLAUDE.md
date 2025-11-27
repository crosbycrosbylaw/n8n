# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`eserv` is a document routing automation system for a law firm. It processes court filing notification emails, downloads documents, matches case names to Dropbox folders using fuzzy matching, and uploads documents to the appropriate client folders.

**Current Implementation Status:**
- ✅ Email HTML parsing and metadata extraction
- ✅ Document download with ASP.NET form handling
- ✅ Dropbox folder index caching with TTL
- ✅ Fuzzy case name matching to folders
- ✅ Multi-file upload orchestration
- ✅ Email state tracking with weekly rotation
- ✅ Pipeline error logging by stage
- ✅ SMTP notifications for uploads/errors
- 🚧 **Next:** Outlook integration for live email monitoring

## Development Commands

### Environment Setup

This project uses Pixi for dependency management and requires Python 3.14+.

```bash
# Run the application
python -m eserv <path_to_html_file>
```

### Testing

```bash
# Run all tests
pixi run test
# or
python -m pytest ./tests

# Run specific test file
python -m pytest tests/eserv/test_<module>.py

# Run with coverage
python -m pytest --cov=eserv ./tests
```

### Git Operations

```bash
# Quick commit and push with timestamp
pixi run push
```

## Architecture

### Core Modules

**Domain Logic:**
-   **`extract.py`** - HTML content extraction using protocol-based extractor pattern
-   **`download.py`** - HTTP download orchestration with ASP.NET form handling
-   **`upload.py`** - Document upload orchestration with Dropbox integration
-   **`main.py`** - Complete pipeline orchestration (parse → download → match → upload → track)

**Utility Subpackage (`util/`):**
-   **`config.py`** - Configuration management with nested dataclasses (SMTP, Dropbox, paths, cache)
-   **`email_state.py`** - Email processing state tracking with weekly rotation and archival
-   **`error_tracking.py`** - Pipeline error logging categorized by stage
-   **`index_cache.py`** - Dropbox folder index caching with configurable TTL
-   **`pdf_utils.py`** - PDF text extraction using PyMuPDF (fitz)
-   **`notifications.py`** - SMTP email notifications for pipeline events
-   **`store.py`** - Document store management
-   **`target_finder.py`** - Fuzzy party name extraction and folder matching

### Key Dependencies

-   `beautifulsoup4` (bs4) - HTML parsing
-   `requests` - HTTP client
-   `dropbox` - Dropbox API client
-   `fitz` (PyMuPDF) - PDF text extraction
-   `rapidfuzz` - Fuzzy string matching for case names
-   `python-dotenv` - Environment variable management
-   `structlog` - Structured logging (wrapped by rampy)
-   `orjson` - Fast JSON serialization
-   `rampy` - Custom utility library from https://github.com/zaynram/ramda-py.git
-   `pytest` - Testing framework

### Code Conventions

-   **Modern Python 3.14+:** Use `T | None` over `Optional[T]`, builtins over typing module aliases
-   **Imports:** `from __future__ import annotations` for forward references
-   **Type checking blocks:** `if typing.TYPE_CHECKING:` for import-only types
-   **Data structures:** Dataclasses with `frozen=True, slots=True` for immutable values
-   **Protocols:** For defining interfaces and abstract contracts
-   **File I/O:** Use `pathlib.Path` and `Path.open()` over built-in `open()`
-   **JSON:** Use `orjson` for all serialization (not standard `json`)
-   **Logging:** Use rampy's structlog wrapper (not base structlog)
-   **Docstrings:** Comprehensive with Args, Returns, Raises sections

### Testing Structure

Tests mirror the source structure in `tests/eserv/`:

-   Main module tests in `tests/eserv/test_<module>.py`
-   Extract functionality tests organized in `tests/eserv/extract/` subdirectory
-   Test utilities and samples in `tests/eserv/utils/`

## Current Development Focus

**Task: Test Upload Integration**

The pipeline is fully implemented but needs integration testing before moving to Outlook automation.

**Testing Priorities:**

1. **Component Testing** - Verify each utility module works:
   - `Config.from_env()` - Loads `.env` correctly
   - `EmailState` - Marks processed, detects duplicates, weekly rotation
   - `ErrorTracker` - Logs errors by pipeline stage
   - `IndexCache` - Refreshes Dropbox folder index
   - `FolderMatcher` - Fuzzy matching with real folder names

2. **End-to-End Pipeline Testing** - Run `main()` with test HTML:
   - Documents download from email
   - Case name extracts correctly
   - Folder match occurs (or triggers manual review)
   - Files upload to Dropbox
   - State tracked in `service/email_state.json`
   - Errors logged to `service/error_log.json`

3. **Edge Cases:**
   - Email with no case name
   - Email with ambiguous case name (manual review path)
   - Duplicate email detection
   - Multiple PDFs in single email
   - Dropbox API errors

**Environment Setup Required:**
- `.env` file configured with Dropbox token and SMTP credentials
- `service/` directory created for state/cache files
- Test HTML email file from real court system

**After Testing:**
Once upload integration is validated, next phase is Outlook integration for live email monitoring.
