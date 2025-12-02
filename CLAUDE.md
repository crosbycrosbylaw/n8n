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
-   ✅ Email state tracking (UID-based audit log)
-   ✅ Pipeline error logging by stage with context manager
-   ✅ SMTP notifications for uploads/errors
-   ✅ OAuth2 credential management (Dropbox + Outlook) with automatic token refresh
-   ✅ Live Outlook email monitoring via Graph API
-   ✅ Custom MAPI flag system for email processing state
-   ✅ Pipeline abstraction and Fire CLI integration
-   🚧 **CRITICAL ISSUES BLOCKING DEPLOYMENT** (see Outstanding Issues below)

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
    -   `process(record: EmailRecord) -> UploadResult` - Process single email
    -   `monitor(num_days: int) -> BatchResult` - Monitor folder and batch process
    -   `execute(record: EmailRecord) -> ProcessedResult` - Process with error handling
-   **`__main__.py`** - Fire CLI entry point (auto-generates subcommands from Pipeline methods)
-   **`extract.py`** - HTML content extraction using protocol-based extractor pattern
-   **`download.py`** - HTTP download orchestration with ASP.NET form handling
-   **`upload.py`** - Document upload orchestration with Dropbox integration

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

**Utility Subpackage (`util/`):**

-   **`config.py`** - Configuration management with nested dataclasses
    -   `SMTPConfig`, `CredentialConfig`, `PathsConfig`, `EmailStateConfig`, `CacheConfig`, `MonitoringConfig`
    -   Lazy credential loading via `CredentialConfig[cred_type]`
-   **`oauth_manager.py`** - `CredentialManager`: OAuth2 token management for Dropbox + Outlook
    -   Lazy token refresh (within 5 min of expiry)
    -   Thread-safe credential updates
    -   Automatic persistence on refresh
-   **`email_state.py`** - `EmailState`: UID-based audit log for processed emails
    -   Fresh start (no weekly rotation, UID primary key)
    -   Overloaded `record()` for flexible input types
    -   `processed` property returns set of UIDs
-   **`error_tracking.py`** - `ErrorTracker`: Pipeline error logging with context manager
    -   `track(uid)` context manager for per-email error isolation
    -   Methods: `error()`, `warning()`, `exception()` all logged to JSON
-   **`index_cache.py`** - Dropbox folder index caching with TTL
-   **`pdf_utils.py`** - PDF text extraction using PyMuPDF (fitz)
-   **`notifications.py`** - SMTP email notifications for pipeline events
-   **`doc_store.py`** - Temporary document store management
-   **`target_finder.py`** - Fuzzy party name extraction and folder matching
-   **`string_validation.py`** - Template validation utilities (currently unused)

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

## Outstanding Issues (CRITICAL – MUST FIX BEFORE DEPLOYMENT)

### 1. EmailState.record() – isinstance() String Literal (BLOCKER)

**File:** `src/eserv/util/email_state.py`, line ~60
**Severity:** CRITICAL – State persistence completely broken

```python
if isinstance(arg, 'ProcessedResult'):  # BUG: string literal
    # This condition is ALWAYS False at runtime
    self._entries[arg.record.uid] = arg
else:
    # All records route here (wrong overload)
    self._entries[arg.uid] = processed_result(arg, error=error)
```

`isinstance()` expects a type object, not a string. **All calls to `record()` take the wrong path**, causing audit log entries to be stored with incorrect structure.

**Fix:** `isinstance(arg, ProcessedResult)` (remove quotes)

**Impact:** Without this fix, the audit log is unusable and deduplication doesn't work.

---

### 2. Pipeline.process() – Return Type Mismatch (BLOCKER)

**File:** `src/eserv/core.py`, line ~99
**Severity:** CRITICAL – Runtime type error

```python
if case_name and state.is_processed(case_name):
    return cons.info('Email already processed, skipping')
    # cons.info() returns None or logging object, NOT UploadResult
```

Type annotation promises `-> UploadResult`, but this returns the result of `console.info()`. Callers expecting `.status` and `.folder_path` attributes will crash at runtime.

**Fix:** Return a proper `UploadResult`:

```python
return UploadResult(status=UploadStatus.NO_WORK, folder_path='', uploaded_files=[])
```

---

### 3. Email Deduplication – UID vs case_name Mismatch (ARCHITECTURAL BLOCKER)

**Files:** `src/eserv/core.py` line ~99, `src/eserv/util/email_state.py`
**Severity:** CRITICAL – Deduplication semantics undefined

The audit log is keyed by **UID** (`{uid: ProcessedResult}`), but Pipeline checks for duplicates by **case_name**:

```python
# core.py
if case_name and state.is_processed(case_name):  # Checking case_name
    return UploadResult(...)

# email_state.py
def is_processed(self, uid: str) -> bool:
    return uid in self._entries  # But entries keyed by uid
```

**These are different identifiers.** A UID is immutable from Graph API; case_name is extracted from email content and may be None or duplicate across emails.

**Decision Required:** What's the deduplication scope?

-   **By UID:** Prevent reprocessing the same email. Check `is_processed(record.uid)` before Pipeline.process().
-   **By case_name:** Prevent uploading the same case twice. Keep current design but fix consistency.

**Recommendation:** Deduplicate by UID (email-level). Case-level deduplication should happen at the Dropbox level (prevent duplicate uploads to same folder).

**Fix:** Change core.py line ~99 to:

```python
if record.uid and state.is_processed(record.uid):
    return UploadResult(status=UploadStatus.NO_WORK, ...)
```

---

### 4. GraphClient Filter Expression – Syntax Error (BLOCKER)

**File:** `src/eserv/monitor/client.py`, line ~121
**Severity:** CRITICAL – All email fetches will fail

```python
filter_expr = f'receivedDateTime ge {start_date}Z and NOT hasAttachments:false'
#                                                              ^ WRONG SYNTAX
```

Graph API OData expects:

-   ✅ `receivedDateTime ge {date}Z` — correct
-   ❌ `hasAttachments:false` — **NOT valid OData syntax**

Should be: `hasAttachments eq false`

**Fix:**

```python
filter_expr = f'receivedDateTime ge {start_date}Z and hasAttachments eq true'
```

**Impact:** Without this fix, the Graph API call will return 400 Bad Request and all emails fail to fetch.

---

### 5. GraphClient Pagination – Silent Data Loss (BLOCKER)

**File:** `src/eserv/monitor/client.py`, line ~131–145
**Severity:** CRITICAL – Silent data loss

```python
result = self._request(
    'GET',
    path=f'/me/mailFolders/{folder_id}/messages',
    params={
        '$filter': filter_expr,
        '$select': 'id,from,subject,receivedDateTime,bodyPreview',
        '$top': 50,  # Only fetches first 50
    },
)
# No pagination loop – if > 50 unprocessed emails, rest are silently ignored
```

Compare to `DocumentUploader._refresh_index_if_needed()` which has:

```python
while True:
    for entry in result.entries:
        # process entry
    if not result.has_more:
        break
    result = self.dbx.files_list_folder_continue(result.cursor)
```

**Fix:** Add pagination loop:

```python
all_records: list[EmailRecord] = []
while True:
    result = self._request(...)
    for msg in result.get('value', []):
        # process msg
        all_records.append(EmailRecord(...))

    if '@odata.nextLink' not in result:
        break
    # Fetch next page (Graph API uses @odata.nextLink for pagination)
```

**Impact:** If >50 unprocessed emails exist, only first 50 are processed each run. Remaining emails accumulate forever.

---

### 6. DocumentUploader Refresh Credentials – Dead Code (HIGH)

**Files:** `src/eserv/core.py` line ~88, `src/eserv/upload.py` line ~71
**Severity:** HIGH – Token refresh cannot work

```python
# core.py
DocumentUploader(
    cache_path=config.cache.index_file,
    dbx_token=config.credentials['dropboxOAuth2Api'].access_token,
    notifier=Notifier(config.smtp),
    manual_review_folder=config.paths.manual_review_folder,
    # NOT PASSING: dbx_app_key, dbx_app_secret, dbx_refresh_token
)

# upload.py __init__
def __init__(self, ..., dbx_app_key: str | None = None, ...):
    # These are None because never passed above
```

The uploader's `_refresh_access_token()` method will always fail because credentials are None.

**Fix:** Pass credentials:

```python
cred = config.credentials['dropboxOAuth2Api']
DocumentUploader(
    ...,
    dbx_app_key=cred.client_id,
    dbx_app_secret=cred.client_secret,
    dbx_refresh_token=cred.refresh_token,
)
```

---

### 7. GraphClient.apply_flag() – MAPI Property Format Untested (HIGH)

**File:** `src/eserv/monitor/client.py`, line ~147
**Severity:** HIGH – Untested integration point

```python
def apply_flag(self, email_uid: str, flag: StatusFlag) -> None:
    with self._lock:
        property_patch = {'singleValueExtendedProperties': [flag]}
        self._request('PATCH', path=f'/me/messages/{email_uid}', json=property_patch)
```

`StatusFlag` is a NewType wrapping `{'id': '...', 'value': '...'}`. The code assumes this structure matches Graph API exactly, but it's **never tested against real Outlook**.

Graph API expects:

```json
{
    "singleValueExtendedProperties": [
        {
            "id": "String {00020329-0000-0000-C000-000000000046} Name eserv_flag",
            "value": "$eserv_success"
        }
    ]
}
```

**Fix:** Add integration test against real Outlook folder (if available) or mock the Graph API response structure explicitly.

---

### 8. EmailState.record() – Overload Signature Mismatch (MEDIUM)

**File:** `src/eserv/util/email_state.py`, line ~53–68
**Severity:** MEDIUM – Type checker will fail

```python
@overload
def record(self, result: ProcessedResult, /) -> None: ...
@overload
def record(self, record: EmailRecord, error: ErrorDict | None, /) -> None: ...
def record(self, arg: EmailRecord | ProcessedResult, error: ErrorDict | None = None) -> None:
    # Implementation signature doesn't match overloads
```

Overload 2 declares `error` as required, but implementation has `error: ... = None` (optional). Mypy will flag this as inconsistent.

**Fix:** Either:

-   Make overload 2 match: `def record(self, record: EmailRecord, error: ErrorDict | None = None, /) -> None: ...`
-   OR restructure to match overloads exactly (separate methods for each path)

---

### 9. GraphClient HTML Body Fetch – Silent Empty String (MEDIUM)

**File:** `src/eserv/monitor/client.py`, line ~140–144
**Severity:** MEDIUM – Silent failure path

```python
body_result = self._request(
    'GET',
    path=f'/me/messages/{uid}',
    params={'$select': 'id,bodyPreview,body'},
)
html_body = body_result.get('body', {}).get('content', '')
```

If Graph API doesn't return a body object, `html_body` becomes empty string. The Pipeline then:

```python
soup = BeautifulSoup(record.html_body, features='html.parser')
```

Empty HTML parses fine, but produces no extractable content. The email silently fails extraction and gets sent to manual review. **No clear error signal.**

**Fix:** Validate non-empty body:

```python
if not html_body:
    raise ValueError(f'Email {uid} has no HTML body')
```

---

## Known Gaps (No Impact on Current Deployment, But Should Plan)

### 10. No Tests for monitor/ Module

The entire `monitor/` package is untested. Risk areas:

-   Filter expression correctness (partially addressed by issue #4)
-   Folder resolution edge cases (deep nesting, special folder names)
-   Error paths (network failure, missing folder, auth failure)
-   Pagination logic (addressed by issue #5)

**Action:** Write unit tests for GraphClient, integration tests for EmailProcessor against mock Graph API.

### 11. Error Tracking Context Never Populated

All `tracker.error()` calls omit the `context` parameter:

```python
raise tracker.error(
    message=f'Failed to download documents: {e!s}',
    stage=PipelineStage.DOCUMENT_DOWNLOAD,
    # context=None (implicit)
)
```

Error logs would be richer with exception details.

**Action:** Add context dict with exception type, traceback, etc.

### 12. Error Log Unbounded Growth

`ErrorTracker` appends indefinitely; `clear_old_errors()` never called automatically.

**Action:** Call `clear_old_errors(days=30)` periodically (e.g., on monitor start).

### 13. GraphClient – No Network Failure Categorization

All API errors treated identically. No distinction between retryable (429, 5xx) and fatal (4xx) errors.

**Action:** Categorize errors and implement retry logic with exponential backoff for transient failures.

### 14. Monitoring Default Folder Path – Hardcoded

Default folder path assumes specific Outlook structure. Likely needs customization per firm.

**Action:** Require explicit MONITORING_FOLDER_PATH config or provide UI for folder selection.

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

**Credentials JSON structure:**

```json
[
    {
        "type": "dropboxOAuth2Api",
        "account": "business",
        "client": { "id": "...", "secret": "..." },
        "data": {
            "token_type": "bearer",
            "scope": "...",
            "access_token": "...",
            "refresh_token": "...",
            "expires_at": "2025-12-01T12:00:00+00:00"
        }
    },
    {
        "type": "microsoftOutlookOAuth2Api",
        "account": "eservice",
        "client": { "id": "...", "secret": "..." },
        "data": {
            "token_type": "bearer",
            "scope": "...",
            "access_token": "...",
            "refresh_token": "...",
            "expires_at": "2025-12-01T12:00:00+00:00"
        }
    }
]
```

## Priority Fix Order (Tomorrow)

In order of criticality:

1. **Fix isinstance() string literal** – email_state.py line ~60
2. **Fix Pipeline.process() return type** – core.py line ~99
3. **Fix Graph API filter syntax** – client.py line ~121
4. **Add pagination loop to GraphClient** – client.py line ~131–145
5. **Clarify UID vs case_name deduplication** – Decision: which scope?
6. **Pass refresh credentials to DocumentUploader** – core.py line ~88
7. **Fix EmailState.record() overload signature** – email_state.py line ~53–68
8. **Write tests for monitor/ module** – New test files needed
9. **Validate HTML body not empty** – client.py line ~140

Without fixes 1–5, the system cannot deploy. Fixes 6–9 should be completed before production use.
