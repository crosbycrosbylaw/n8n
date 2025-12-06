#!/usr/bin/env python3

# pyright: reportAttributeAccessIssue = false, reportUnknownMemberType = false, reportUnknownArgumentType = false, reportUnknownVariableType = false

"""Manual test script for eserv integration testing.

This script provides interactive testing capabilities for validating
the eserv pipeline before running with real court emails.

Usage:
    python test_manual.py [--check-config] [--check-dropbox] [--test-sample]
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any

from rampy import console, test

cons = console.bind()


@contextmanager
def temp_dir():
    path = test.directory('tmp')
    try:
        yield path
    finally:
        path.clean()


def check_config() -> bool:
    """Verify environment configuration is correct."""
    cons.info('Checking configuration...')

    try:
        from automate.eserv.util import Config

        config = Config.from_env()

        cons.info('Configuration loaded successfully')
        cons.info('SMTP Server', server=config.smtp.server, port=config.smtp.port)
        cons.info('Service Directory', path=config.paths.service_dir.as_posix())
        cons.info('Cache TTL', hours=config.cache.ttl_hours)
        cons.info('Manual Review Folder', folder=config.paths.manual_review_folder)

    except Exception:
        cons.exception('Configuration check failed')
        return False

    else:
        return True


def check_dropbox() -> bool:
    """Verify Dropbox connection and list folders."""
    cons.info('Checking Dropbox connection...')

    try:
        import dropbox

        from automate.eserv.util import Config

        config = Config.from_env()
        dbx = dropbox.Dropbox(config.dropbox.token)

        # Test connection with account info
        account = dbx.users_get_current_account()
        cons.info('Connected to Dropbox', account=account.name.display_name)

        # List folders in root
        cons.info('Fetching folder list...')
        result = dbx.files_list_folder('')

        folders = [
            entry.path_display
            for entry in result.entries
            if isinstance(entry, dropbox.files.FolderMetadata)
        ]

        cons.info('Found folders', count=len(folders))

        folders_head = 10  # Show first 10

        for folder in folders[:folders_head]:
            cons.info('Folder', path=folder)

        if len(folders) > folders_head:
            cons.info('... and more', additional=len(folders) - folders_head)

    except ImportError:
        cons.error('Dropbox SDK not installed')
        return False

    except Exception:
        cons.exception('Dropbox connection failed')
        return False

    else:
        return True


def test_sample_email() -> bool:
    """Test pipeline with sample email (without actual download/upload)."""
    cons.info('Testing with sample email...')

    try:
        # Write sample email to temp file

        from bs4 import BeautifulSoup

        from automate.eserv.extract import extract_download_info, extract_upload_info
        from tests.eserv.lib import SAMPLE_EMAIL

        # Parse email
        soup = BeautifulSoup(SAMPLE_EMAIL, 'html.parser')

        cons.info('Parsed email HTML')

        # Extract upload info (without downloading)
        # Note: This will fail on document download since we don't have a real file
        # But we can at least validate the parsing works
        download_info = extract_download_info(soup)

        if (doc_source := download_info.source) and (doc_name := download_info.doc_name):
            cons.info('Extracted document name', name=doc_source)
            cons.info('Extracted document name', name=doc_name)
        else:
            return False

        with temp_dir() as tmp:
            upload_info = extract_upload_info(soup, tmp)

        if case_name := upload_info.case_name:
            cons.info('Extracted case name', name=case_name)
        else:
            return False

        cons.info('Sample email test completed')
        cons.info('Note: Full pipeline test requires real document download link')

    except Exception:
        cons.exception('Sample email test failed')
        return False

    else:
        return True


def main() -> int:
    """Run manual integration tests."""
    cons.info('eserv Manual Integration Test')

    tests = []

    if '--check-config' in sys.argv or len(sys.argv) == 1:
        tests.append(('Configuration Check', check_config))

    if '--check-dropbox' in sys.argv or len(sys.argv) == 1:
        tests.append(('Dropbox Connection', check_dropbox))

    if '--test-sample' in sys.argv or len(sys.argv) == 1:
        tests.append(('Sample Email Parse', test_sample_email))

    results: list[tuple[str, Any]] = []
    for name, test_func in tests:
        print(f'\n[ {name} ]')
        result = test_func()
        results.append((name, result))

    cons.info('\n\nResults:')

    for name, passed in results:
        func, status = (cons.info, '[PASS]') if passed else (cons.error, '[FAIL]')
        func(f'{status} {name}')

    all_passed = all(result for _, result in results)

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
