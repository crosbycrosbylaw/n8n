# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Memorizations

-   assume python version >=3.14
-   prefer abstraction to reusable functions over repetitive implementations
-   prefer concise variable names
-   always update claude.md to reflect changes made in edits

## Project Overview

`eserv` is a document routing automation system for a law firm. It processes court filing notification emails, downloads documents, matches case names to Dropbox folders using fuzzy matching, and uploads documents to the appropriate client folders.

**Implemented Features:**

-   Email HTML parsing and metadata extraction
-   Document download with ASP.NET form handling
-   Dropbox folder index caching with TTL
-   Fuzzy case name matching to folders
-   Multi-file upload orchestration
-   Email state tracking (UID-based audit log)
-   Pipeline error logging by stage with rich context
-   SMTP notifications for uploads/errors
-   OAuth2 credential management (Dropbox + Outlook) with automatic token refresh
-   Live Outlook email monitoring via Graph API
-   Custom MAPI flag system for email processing state
-   Pipeline abstraction and Fire CLI integration
-   Network retry logic with exponential backoff
-   Automatic error log maintenance

## Development Commands

### Environment Setup

This project uses Pixi for dependency management and requires Python 3.14+.

```bash
# Process single email HTML file
python -m eserv process --body "<html>...</html>" --subject "Case Name" --sender "court@example.com"

# Monitor Outlook folder and process emails from past N days
python -m eserv monitor --num_days 1
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

**Pipeline & Orchestration:**

-   **`core.py`** - `Pipeline` class: unified interface for both file-based and monitoring modes
    -   `process(record: EmailRecord) -> IntermediaryResult` - Process single email
    -   `monitor(num_days: int) -> BatchResult` - Monitor folder and batch process
    -   `execute(record: EmailRecord) -> ProcessedResult` - Process single email with error handling
-   **`__main__.py`** - Fire CLI entry point (auto-generates subcommands from Pipeline methods)
-   **`extract.py`** - HTML content extraction using protocol-based extractor pattern
-   **`record.py`** - EmailRecord factory
    -   `email_record()` - Create EmailRecord from HTML string, subject, sender
-   **`stages/download.py`** - HTTP download orchestration with ASP.NET form handling
    -   `download_documents()` - Main download orchestration function
-   **`stages/upload.py`** - Document upload orchestration with Dropbox integration
    -   `upload_documents()` - Main upload orchestration function
    -   `DropboxManager` - Dropbox client management with token refresh
-   **`stages/types.py`** - Upload result types: `IntermediaryResult`, `UploadStatus`
-   **`types.py`** - Barrel export module for core type definitions

**Email Monitoring (`monitor/`):**

-   **`client.py`** - `GraphClient`: Microsoft Graph API client
    -   Folder hierarchy resolution with caching
    -   Unprocessed email fetching (date range + UID exclusion)
    -   Thread-safe MAPI flag application
-   **`processor.py`** - `EmailProcessor`: Orchestration (fetch → process → flag → audit)
-   **`flags.py`** - Email flag system: `StatusFlag` enum (success, error categories)
-   **`types.py`** - Dataclasses: `EmailRecord`, `EmailInfo`, `ProcessedResult`, `BatchResult`
-   **`result.py`** - Result conversion utilities: `processed_result()` factory

**Error Handling (`errors/`):**

-   **`_core.py`** - `PipelineError`: Exception with stage and error info
-   **`_config.py`** - Config-specific exceptions: `MissingVariableError`, `InvalidFormatError`

**Credential Management (`util/oauth_manager.py`):**

-   **`CredentialManager`** - OAuth2 token management for Dropbox + Outlook
    -   Unified refresh mechanism using `requests.post()` for both credential types
    -   Lazy token refresh (within 5 min of expiry)
    -   Thread-safe credential updates with locking
    -   Automatic persistence on refresh
    -   Flat JSON serialization (no nested dicts)
-   **`OAuthCredential`** - Immutable credential dataclass
    -   Pure data container (no client storage)
    -   `update_from_refresh()` method creates new instances (immutable pattern)
    -   `refresh()` method orchestrates token refresh via handlers
    -   `export()` serializes to flat JSON structure
-   **Refresh handlers**:
    -   `_refresh_dropbox()` - Dropbox OAuth2 token refresh
    -   `_refresh_outlook()` - Microsoft OAuth2 token refresh
    -   Both use identical `requests.post()` pattern

**Utility Subpackage (`util/`):**

-   **`configuration.py`** - Configuration management with nested dataclasses
    -   `SMTPConfig`, `CredentialConfig`, `PathsConfig`, `EmailStateConfig`, `CacheConfig`, `MonitoringConfig`
    -   Lazy credential loading via `CredentialConfig[cred_type]`
-   **`email_state.py`** - `EmailState`: UID-based audit log for processed emails
    -   Fresh start (no weekly rotation, UID primary key)
    -   Overloaded `record()` for flexible input types
    -   `processed` property returns set of UIDs
    -   `clear_flags()` method allows manual reprocessing of emails
-   **`error_tracking.py`** - `ErrorTracker`: Pipeline error logging with context manager
    -   `track(uid)` context manager for per-email error isolation
    -   Methods: `error()`, `warning()`, `exception()` all logged to JSON
-   **`index_cache.py`** - Dropbox folder index caching with TTL
-   **`pdf_utils.py`** - PDF text extraction using PyMuPDF (fitz)
-   **`notifications.py`** - SMTP email notifications for pipeline events
-   **`doc_store.py`** - Temporary document store management
-   **`target_finder.py`** - Fuzzy party name extraction and folder matching
-   **`types.py`** - Barrel export module for util type definitions

### Key Dependencies

-   `beautifulsoup4` (bs4) - HTML parsing
-   `requests` - HTTP client + OAuth2 token refresh
-   `dropbox` - Dropbox SDK
-   `pymupdf` (fitz) - PDF text extraction
-   `rapidfuzz` - Fuzzy string matching
-   `python-dotenv` - Environment variable loading
-   `structlog` + `rampy` - Structured logging
-   `orjson` - Fast JSON serialization
-   `fire` - CLI generation from Python objects
-   `pytest` - Testing framework

### Code Conventions

-   **Modern Python 3.14+:** Use `T | None` over `Optional[T]`, builtins over typing module aliases
-   **Imports:** `from __future__ import annotations` for forward references
-   **Type checking blocks:** `if typing.TYPE_CHECKING:` for import-only types
-   **Data structures:** Dataclasses with `frozen=True, slots=True` for immutable values; mutable dataclasses for mutable state
-   **Protocols:** For defining interfaces and abstract contracts
-   **File I/O:** Use `pathlib.Path` and `Path.open()` over built-in `open()`
-   **JSON:** Use `orjson` for all serialization
-   **Logging:** Use rampy's structlog wrapper
-   **Error handling:** Typed exceptions (`PipelineError`) with stage/message; context managers for error tracking
-   **Docstrings:** Comprehensive with Args, Returns, Raises sections
-   **Type re-exports:** Subpackages use `types.py` as barrel modules to cleanly expose public types
-   **Testing:** Follow standardized patterns defined in `tests/TESTING_STANDARDS.md`:
    -   Pattern A (Scenario Factory) for data-driven tests
    -   Pattern B (Fixture Class) for complex mocking
    -   Pattern C (Class-Based) for logical grouping
    -   Pattern D (Mock Factory) optional optimization for repetitive patching (10+ tests with identical patches)

## Development History

### Mock Factory Pattern Standardization (December 2025)

**Enhancement:** Standardized `mock_core_factory` pattern across all 17 tests in `test_core.py`.

**Changes:**

-   **Pattern D documented** - Added Mock Factory Pattern to `tests/TESTING_STANDARDS.md` as optional optimization
-   **Full adoption in test_core.py** - Converted all 17 tests from verbose patching to `mock_core_factory`
-   **Code reduction** - Eliminated ~48 lines of repetitive boilerplate (3 patches × 16 tests)
-   **Type safety** - Uses Literal types to prevent typos in dependency names
-   **Deleted tests/utils.py** - Removed unused generalized mock factory (over-engineered, sacrifices type safety)
-   **Module-specific approach** - Each test file defines its own factory for better ergonomics and type safety
-   **Benefits**: DRY principle, maintainability, consistency across tests
-   **Tradeoffs**: Adds indirection, less explicit import paths

**When to use:**

-   File has 10+ tests with identical patch patterns
-   All tests patch same module with same dependencies
-   Benefits of DRY outweigh cost of indirection

**Result:** All 131 tests passing. Pattern documented as optional enhancement for files with substantial repetition.

### Test Core Mock Assertion Fix (December 2025)

**Fix:** Fixed failing test in `test_core.py::TestPipelineMonitor::test_error_log_cleanup_before_processing`.

**Issue:** Test was asserting against `mock_dependencies['tracker']` but the Pipeline was using a real ErrorTracker instance because the `error_tracker` patch was missing.

**Resolution:** Added missing `patch('automate.eserv.core.error_tracker', return_value=mock_dependencies['tracker'])` to match the pattern used in all other tests in the file. This ensures the Pipeline receives the mock tracker so assertions work correctly.

**Result:** All 131 tests now passing with 0 failures and 0 skipped tests.

### Email State Clear Flags Test Coverage (December 2025)

**Fix:** Replaced skipped "rotation feature removed" test with comprehensive tests for `clear_flags()` method.

**Changes:**

-   **Removed skipped test** - Deleted placeholder test for removed rotation feature
-   **Added 3 new tests** - Comprehensive coverage of `clear_flags()` functionality:
    -   `test_clear_flags_removes_uid` - Verifies flag removal from processed set
    -   `test_clear_flags_persists_removal` - Tests persistence across instances
    -   `test_clear_flags_nonexistent_uid_is_noop` - Validates graceful handling of nonexistent UIDs
-   **Test suite now has 0 skipped tests** - All tests passing

### Test Suite Standardization (December 2025)

**Major refactoring:** Standardized testing patterns across all test files for consistency and maintainability.

**Improvements:**

-   **Created comprehensive testing standards** - Documented three distinct testing patterns (Scenario Factory, Fixture Class, Class-Based) in `tests/TESTING_STANDARDS.md`
-   **Pattern A (Scenario Factory)** - For data-driven tests with scenario factory functions returning dicts; uses `@test.scenarios` decorator
-   **Pattern B (Fixture Class)** - For complex mock orchestration using `@fixture_class` and `test.subtestfix`; context managers for patches
-   **Pattern C (Class-Based)** - For traditional unit tests with logical grouping
-   **Migrated test_processor.py** - Converted from dataclass scenarios to factory functions (simpler, more consistent)
-   **Migrated test_email_state.py** - Removed complex conditional logic; split into separate test classes; uses tempdir fixture from conftest
-   **Migrated test_extract_aspnet_form.py** - Renamed generic `scenario()` to `aspnet_form_scenario()`; renamed `exception` to `should_raise`; cleaner exception handling

**Standardized conventions:**

-   Scenario factory functions named `{component}_scenario`
-   Positional-only `self` parameter (`/`) for scenario tests
-   `rampy.test.directory()` for tempdir management (not manual tempfile/shutil)
-   `should_raise` parameter for exception testing
-   Descriptive docstrings on all test classes and factories

**Reference implementations:**

-   Pattern A: `tests/eserv/util/test_target_finder.py`
-   Pattern B: `tests/eserv/stages/conftest.py` + `tests/eserv/stages/test_upload.py`
-   Pattern C: `tests/eserv/test_core.py`

### Credential Management Simplification (December 2025)

**Major refactoring:** Reduced credential management complexity from ~661 lines to ~490 lines (-26%).

**Improvements:**

-   **Unified refresh mechanism** - Single `requests.post()` pattern for both Dropbox and Outlook (removed 50-line RefreshConfig class)
-   **Removed redundant client storage** - OAuthCredential is now a pure data container; DropboxManager owns client instances
-   **Eliminated double refresh** - Removed unnecessary refresh() call in DropboxManager; trust CredentialManager's expiry logic
-   **Immutable credential updates** - `update_from_refresh()` uses dataclass `replace()` for clean, predictable state changes
-   **Flat JSON serialization** - Simplified credentials.json format (no nested 'client' or 'data' dicts)
-   **Migration tooling** - `scripts/migrate_credentials.py` automates conversion from old to new format

**Test coverage:** Added comprehensive `test_oauth_manager.py` with 100+ assertions covering all refresh, update, and serialization paths.

### Bug Fixes Summary (December 2025)

**28 critical issues resolved** across three analysis passes. All known runtime crashes, type errors, and API mismatches have been fixed.

**Key fixes included:**

-   Email deduplication logic (UID-based instead of case_name)
-   Graph API pagination and filter syntax
-   OAuth credential loading and JSON field filtering
-   Dataclass default_factory errors
-   Exception handling (bare except clauses)
-   Test file API alignment and stub implementations

**Critical architectural change:** Removed `frozen=True` from RefreshConfig and OAuthCredential dataclasses to simplify credential update logic while retaining `slots=True` for performance.

---

## Current Test Status

**Test Results (as of December 2025):**

-   ✅ **131 tests passing**
-   ⏭️ **0 tests skipped**
-   ❌ **0 failures**
-   ❌ **0 errors**

**Test Coverage by Module:**

-   ✅ `extract/` - Full coverage (6 test files, 26 tests)
-   ✅ `monitor/` - Full coverage (test_client.py + test_processor.py, 20 tests)
-   ✅ `util/` - Partial coverage (5 test files, 62 tests)
-   ✅ `stages/upload.py` - Full coverage (TestDropboxManager + orchestration tests)
-   ✅ `stages/download.py` - Full coverage (14 tests)
-   ✅ `test_core.py` - Full coverage (17 tests, all passing)
-   ✅ `test_integration.py` - Basic workflows covered (4 tests)

---

## Outstanding Tasks

### 1. Test File Completion

The following test files need to be created or completed to achieve comprehensive test coverage before deployment:

#### HIGH Priority - Core Pipeline Tests

**`tests/eserv/test_core.py`** (NEW - CRITICAL)

-   Test `Pipeline.process()` workflow with real email records
-   Test `Pipeline.monitor()` batch processing
-   Test `Pipeline.execute()` error handling and state tracking
-   Mock Dropbox/Graph API calls for isolated testing
-   **Importance:** Core orchestration logic currently untested

**`tests/eserv/stages/test_upload.py`** (REWRITE REQUIRED)

-   **Current State:** 8 tests skipped (deprecated DocumentUploader API)
-   **Required Changes:**
    -   Rewrite TestDocumentUploaderTokenRefresh for current OAuthCredential handler mechanism
    -   Rewrite TestDocumentUpload to use `upload_documents()` function and `DropboxManager`
    -   Test scenarios: successful upload, manual review paths, token refresh, error handling
    -   Mock Dropbox SDK operations (files_upload, files_list_folder)
-   **Importance:** Upload orchestration is core functionality

**`tests/eserv/stages/test_download.py`** (NEW)

-   Test `download_documents()` workflow
-   Test ASP.NET form handling and submission
-   Test multi-file download orchestration
-   Mock HTTP requests for file downloads
-   **Importance:** Download failures would break entire pipeline

**`tests/eserv/monitor/test_processor.py`** (NEW)

-   Test `EmailProcessor.process_emails()` orchestration
-   Test error handling and MAPI flag application
-   Test batch processing with multiple emails
-   Mock GraphClient and Pipeline interactions
-   **Importance:** Email monitoring orchestration currently untested

#### MEDIUM Priority - Utility Tests

**`tests/eserv/util/test_oauth_manager.py`** (NEW)

-   Test `CredentialManager._load()` credential loading
-   Test `OAuthCredential` token refresh handlers (\_refresh_dropbox, \_refresh_outlook)
-   Test token expiration detection and auto-refresh
-   Test credential persistence
-   Mock OAuth2 API token refresh endpoints
-   **Importance:** Token refresh failures would cause authentication errors

**`tests/eserv/util/test_notifications.py`** (NEW)

-   Test `Notifier` SMTP email sending
-   Test notification formatting for success/error scenarios
-   Mock SMTP server connection
-   **Importance:** Notification failures are not critical but reduce visibility

**`tests/eserv/util/test_pdf_utils.py`** (NEW)

-   Test `extract_text_from_pdf()` with sample PDFs
-   Test error handling for corrupted/empty PDFs
-   Test `extract_case_names_from_pdf()` party name extraction
-   **Importance:** PDF parsing errors affect case name matching

**`tests/eserv/monitor/test_flags.py`** (NEW)

-   Test `StatusFlag` enum values and MAPI property mapping
-   Test flag color assignments
-   **Importance:** Low priority (simple enum, minimal logic)

#### LOW Priority - Optional

**`tests/eserv/util/test_doc_store.py`** (OPTIONAL)

-   Test temporary document store cleanup
-   Test file path generation
-   **Importance:** Simple utility, minimal complexity

**`tests/eserv/__main__.py`** (OPTIONAL)

-   Manual test for configuration and environment checks
-   **Importance:** Useful for developer onboarding, can identify non-implementation errors

### 2. Code Coverage Goals

Before deployment, achieve the following coverage targets:

-   **Overall:** >80% code coverage
-   **Core modules (core.py, stages/upload.py, stages/download.py):** >90% coverage
-   **Monitor module:** >90% coverage (currently at ~80%)
-   **Util module:** >85% coverage (currently at ~70%)

Run coverage analysis:

```bash
python -m pytest --cov=eserv --cov-report=html ./tests
```

### 3. Pre-Deployment Checklist

Before considering the package deployment-ready, complete the following:

#### Testing & Quality

-   [ ] All HIGH priority test files created and passing
-   [ ] Overall test coverage >80%
-   [ ] All skipped tests either completed or documented as intentionally skipped
-   [ ] Integration tests cover all major workflows (process, monitor, error handling)
-   [ ] Manual testing of OAuth2 token refresh for both Dropbox and Outlook

#### Documentation

-   [ ] Update CLAUDE.md with final test coverage statistics
-   [ ] Document any known limitations or edge cases
-   [ ] Update environment setup instructions if needed
-   [ ] Document deployment procedure (systemd service, cron job, etc.)

#### Configuration & Security

-   [ ] Verify credentials.json format matches documented structure
-   [ ] Test with production-like .env configuration
-   [ ] Verify SMTP credentials work with production email server
-   [ ] Test Graph API permissions with production Outlook account
-   [ ] Verify Dropbox folder structure matches expected layout

#### Production Readiness

-   [ ] Test monitor mode with real emails from past 7 days
-   [ ] Verify error tracking logs meaningful diagnostics
-   [ ] Test SMTP notifications reach intended recipients
-   [ ] Verify automatic error log cleanup works (30-day retention)
-   [ ] Test graceful shutdown (SIGTERM handling)

#### Performance & Reliability

-   [ ] Test network retry logic with simulated transient failures
-   [ ] Verify pagination handles >50 emails correctly
-   [ ] Test concurrent email processing (if applicable)
-   [ ] Verify index cache TTL refresh works correctly
-   [ ] Monitor memory usage during batch processing

---

## System Status

**Production Readiness:** ⚠️ **TESTING IN PROGRESS**

28 critical bugs have been fixed, and core functionality is stable. However, test coverage gaps remain in core orchestration modules (Pipeline, upload, download, processor). Complete HIGH priority tests before production deployment.

---

## Environment Setup

**.env file:**

```
# Dropbox + Outlook OAuth2 credentials
CREDENTIALS_PATH=/path/to/credentials.json

# Monitoring configuration
MONITORING_LOOKBACK_DAYS=1
MONITORING_FOLDER_PATH=Inbox/File Handling - All/Filing Accepted / Notification of Service / Courtesy Copy

# SMTP notifications
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_FROM_ADDR=notify@law-firm.com
SMTP_TO_ADDR=attorney@law-firm.com
SMTP_USERNAME=notify@law-firm.com
SMTP_PASSWORD=app-specific-password
SMTP_USE_TLS=true

# Dropbox manual review folder
MANUAL_REVIEW_FOLDER=/Clio/Manual Review/

# Service directory (auto-created if not specified)
SERVICE_DIR=/path/to/service/dir
INDEX_CACHE_TTL_HOURS=4
```

**Credentials JSON structure (flat format):**

```json
[
    {
        "type": "dropbox",
        "account": "business",
        "client_id": "...",
        "client_secret": "...",
        "token_type": "bearer",
        "scope": "files.content.write files.metadata.read",
        "access_token": "...",
        "refresh_token": "...",
        "expires_at": "2025-12-01T12:00:00+00:00"
    },
    {
        "type": "microsoft-outlook",
        "account": "eservice",
        "client_id": "...",
        "client_secret": "...",
        "token_type": "bearer",
        "scope": "Mail.Read offline_access",
        "access_token": "...",
        "refresh_token": "...",
        "expires_at": "2025-12-01T12:00:00+00:00"
    }
]
```

**Migrating from old format:**

If you have an existing credentials.json file with the old nested format (with 'client' and 'data' subdicts), run the migration script:

```bash
python scripts/migrate_credentials.py /path/to/credentials.json
```

The script will:

-   Create a timestamped backup of your original file
-   Convert to the new flat format
-   Preserve all credential data

````

## Testing

Run the test suite to validate all fixes and monitor coverage:

```bash
# Run all tests
python -m pytest ./tests -v

# Run specific module tests
python -m pytest tests/eserv/monitor/ -v
python -m pytest tests/eserv/util/ -v
python -m pytest tests/eserv/stages/ -v

# Run with coverage report
python -m pytest --cov=eserv --cov-report=term-missing ./tests

# Generate HTML coverage report
python -m pytest --cov=eserv --cov-report=html ./tests
# View at: htmlcov/index.html
````

**Bug Fix Summary:** 28 critical issues resolved (Issues #1-28 across three passes). Core functionality is stable, but test coverage gaps remain. See "Outstanding Tasks" section above for pre-deployment requirements.
