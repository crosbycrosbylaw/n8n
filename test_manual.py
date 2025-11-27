#!/usr/bin/env python3
"""Manual test script for eserv integration testing.

This script provides interactive testing capabilities for validating
the eserv pipeline before running with real court emails.

Usage:
    python test_manual.py [--check-config] [--check-dropbox] [--test-sample]
"""

from __future__ import annotations

import sys
from pathlib import Path

from rampy import console

log = console.bind()


def check_config() -> bool:
    """Verify environment configuration is correct."""
    log.info('Checking configuration...')

    try:
        from eserv.util import Config

        config = Config.from_env()

        log.info('Configuration loaded successfully')
        log.info('SMTP Server', server=config.smtp.server, port=config.smtp.port)
        log.info('Service Directory', path=config.paths.service_dir.as_posix())
        log.info('Cache TTL', hours=config.cache.ttl_hours)
        log.info('Manual Review Folder', folder=config.paths.manual_review_folder)

        return True

    except Exception as e:
        log.exception('Configuration check failed')
        return False


def check_dropbox() -> bool:
    """Verify Dropbox connection and list folders."""
    log.info('Checking Dropbox connection...')

    try:
        import dropbox  # type: ignore
        from eserv.util import Config

        config = Config.from_env()
        dbx = dropbox.Dropbox(config.dropbox.token)

        # Test connection with account info
        account = dbx.users_get_current_account()
        log.info('Connected to Dropbox', account=account.name.display_name)

        # List folders in root
        log.info('Fetching folder list...')
        result = dbx.files_list_folder('')

        folders = [entry.path_display for entry in result.entries if isinstance(entry, dropbox.files.FolderMetadata)]

        log.info('Found folders', count=len(folders))
        for folder in folders[:10]:  # Show first 10
            log.info('Folder', path=folder)

        if len(folders) > 10:
            log.info('... and more', additional=len(folders) - 10)

        return True

    except ImportError:
        log.error('Dropbox SDK not installed')
        return False
    except Exception as e:
        log.exception('Dropbox connection failed')
        return False


def test_sample_email() -> bool:
    """Test pipeline with sample email (without actual download/upload)."""
    log.info('Testing with sample email...')

    try:
        from tests.eserv.utils import SAMPLE_EMAIL
        from bs4 import BeautifulSoup
        from eserv.util import Config
        from eserv.extract import extract_upload_info

        # Write sample email to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(SAMPLE_EMAIL)
            email_path = Path(f.name)

        log.info('Created sample email', path=email_path.as_posix())

        # Parse email
        with email_path.open() as f:
            soup = BeautifulSoup(f, 'html.parser')

        log.info('Parsed email HTML')

        # Extract upload info (without downloading)
        # Note: This will fail on document download since we don't have a real file
        # But we can at least validate the parsing works

        case_name = soup.find('td', string='Case Name')
        if case_name:
            case_value = case_name.find_next_sibling('td')
            log.info('Extracted case name', name=case_value.text if case_value else None)

        # Clean up
        email_path.unlink()

        log.info('Sample email test completed')
        log.info('Note: Full pipeline test requires real document download link')

        return True

    except Exception as e:
        log.exception('Sample email test failed')
        return False


def main() -> int:
    """Run manual integration tests."""
    print('eserv Manual Integration Test')
    print('=' * 60)

    tests = []

    if '--check-config' in sys.argv or len(sys.argv) == 1:
        tests.append(('Configuration Check', check_config))

    if '--check-dropbox' in sys.argv or len(sys.argv) == 1:
        tests.append(('Dropbox Connection', check_dropbox))

    if '--test-sample' in sys.argv or len(sys.argv) == 1:
        tests.append(('Sample Email Parse', test_sample_email))

    results = []
    for name, test_func in tests:
        print(f'\n--- {name} ---')
        result = test_func()
        results.append((name, result))

    print('\n' + '=' * 60)
    print('Test Results:')
    for name, passed in results:
        status = '[PASS]' if passed else '[FAIL]'
        print(f'{status} {name}')

    all_passed = all(result for _, result in results)
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
