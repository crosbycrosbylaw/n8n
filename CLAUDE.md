# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`eserv` is a document routing automation system for a law firm. It processes court filing notification emails, downloads documents, matches case names to Dropbox folders using fuzzy matching, and uploads documents to the appropriate client folders.

**Current Implementation Status:**

-   ✅ Email HTML parsing and metadata extraction
-   ✅ Document download with ASP.NET form handling
-   ✅ Dropbox folder index caching with TTL
-   ✅ Fuzzy case name matching to folders
-   ✅ Multi-file upload orchestration
-   ✅ Email state tracking with weekly rotation
-   ✅ Pipeline error logging by stage
-   ✅ SMTP notifications for uploads/errors
-   ✅ Comprehensive test suite (58 passing tests)
-   ✅ Integration testing for upload workflows
-   🚧 **Next:** Live email monitoring with Outlook/IMAP integration

## Development Commands

### Environment Setup

This project uses Pixi for dependency management and requires Python 3.14+.

```bash
# Run the application
python -m eserv <path_to_html_file>
```

### Testing

```bash
# Run all tests (58 tests, ~0.8s)
pixi run test
# or
python -m pytest ./tests

# Run specific test file
python -m pytest tests/eserv/test_<module>.py

# Run specific test suite
python -m pytest tests/eserv/util/          # Utility tests
python -m pytest tests/eserv/extract/       # Extraction tests
python -m pytest tests/test_integration.py  # Integration tests

# Run with coverage
python -m pytest --cov=eserv ./tests

# Run with verbose output
python -m pytest -v ./tests
```

### Git Operations

```bash
# Quick commit and push with timestamp
pixi run push
```

## Architecture

### Core Modules

**Domain Logic:**

-   **`__main__.py`** - CLI entry point with argparse for path input
-   **`main.py`** - Complete pipeline orchestration (parse → download → match → upload → track)
-   **`extract.py`** - HTML content extraction using protocol-based extractor pattern
-   **`download.py`** - HTTP download orchestration with ASP.NET form handling
-   **`upload.py`** - Document upload orchestration with Dropbox integration and automatic token refresh

**Utility Subpackage (`util/`):**

-   **`config.py`** - Configuration management with nested dataclasses (SMTP, Dropbox, paths, cache)
-   **`email_state.py`** - Email processing state tracking with weekly rotation and archival
-   **`error_tracking.py`** - Pipeline error logging categorized by stage
-   **`index_cache.py`** - Dropbox folder index caching with configurable TTL
-   **`pdf_utils.py`** - PDF text extraction using PyMuPDF (fitz)
-   **`notifications.py`** - SMTP email notifications for pipeline events
-   **`doc_store.py`** - Temporary document store management for downloads
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

**Test Organization (58 passing tests):**

-   **Unit Tests** (`tests/eserv/`)
    -   `util/test_*.py` - Utility module tests (config, email state, error tracking, caching, folder matching)
    -   `extract/test_*.py` - HTML extraction tests (ASP.NET forms, URLs, file metadata)
    -   `test_upload.py` - Dropbox upload and token refresh tests
-   **Integration Tests** (`tests/test_integration.py`)
    -   Complete workflow testing (successful upload, manual review, duplicate detection)
    -   Environment configuration validation
-   **Test Utilities** (`tests/eserv/utils/`)
    -   Sample email generation
    -   Test fixtures and helpers

**Test Conventions:**
-   Uses `rampy.test.scenarios` pattern for consistency
-   Tests follow Given-When-Then structure
-   Parametrized tests using pytest fixtures

## Current Development Focus

**Phase: Email Monitoring Integration**

The core pipeline is fully implemented and tested (58/58 tests passing). Ready for live email monitoring integration.

**Completed:**

-   ✅ **Component Testing** - All utility modules validated:
    -   `Config.from_env()` - Environment variable loading and validation
    -   `EmailState` - Processing tracking, duplicate detection, weekly rotation
    -   `ErrorTracker` - Stage-based error logging with context
    -   `IndexCache` - Dropbox folder caching with TTL
    -   `FolderMatcher` - Fuzzy matching with confidence scoring
-   ✅ **Integration Testing** - Complete workflows tested:
    -   Successful upload to matched folders
    -   Manual review workflow for ambiguous cases
    -   Duplicate email detection and skipping
    -   State persistence across restarts
-   ✅ **Edge Case Handling** - Tested scenarios:
    -   Missing/ambiguous case names → manual review
    -   Multiple PDFs in single email
    -   Token refresh for expired Dropbox credentials
    -   Error logging at each pipeline stage

**Next Steps:**

1. **Outlook/IMAP Integration**
    -   Monitor designated inbox for new court filing emails
    -   Filter by sender/subject patterns
    -   Extract HTML body and pass to pipeline
    -   Mark emails as processed in inbox
2. **Production Deployment**
    -   Set up Windows service or scheduled task
    -   Configure monitoring frequency
    -   Set up alerting for critical failures
    -   Document operational procedures

**Environment Setup:**

-   `.env` file with Dropbox token and SMTP credentials
-   `service/` directory auto-created for state/cache files
-   Outlook/Exchange credentials for email access

## Testing Status

**Last Test Run:** November 26, 2025
**Result:** ✅ All 58 tests passing (0.79s)
**Test Report:** See commit `2437e24` for detailed integration test report

**Test Coverage by Module:**
-   Configuration loading and validation
-   Email state tracking and rotation
-   Error logging by pipeline stage
-   Dropbox folder caching and staleness detection
-   Fuzzy case name matching
-   Document download with ASP.NET form handling
-   Dropbox upload with token refresh
-   Complete end-to-end workflows (success, manual review, duplicates)
