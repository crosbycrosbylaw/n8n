#!/usr/bin/env python3
"""Migration script to convert credentials.json from nested to flat format.

Usage:
    python scripts/migrate_credentials.py /path/to/credentials.json

This script will:
1. Read the old nested format credentials file
2. Convert to new flat format
3. Create a backup of the original file
4. Write the new flat format to the original path
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson


def migrate_credential(old_format: dict[str, Any]) -> dict[str, Any]:
    """Convert a single credential from nested to flat format.

    Args:
        old_format: Credential in nested format with 'client' and 'data' dicts

    Returns:
        Credential in flat format with all fields at top level

    """
    flat: dict[str, Any] = {}

    # Copy top-level fields
    flat['type'] = old_format['type']
    flat['account'] = old_format['account']

    # Flatten client fields
    if 'client' in old_format:
        flat['client_id'] = old_format['client']['id']
        flat['client_secret'] = old_format['client']['secret']

    # Flatten data fields
    if 'data' in old_format:
        data = old_format['data']
        flat['token_type'] = data['token_type']
        flat['scope'] = data['scope']
        flat['access_token'] = data['access_token']
        flat['refresh_token'] = data['refresh_token']

        # Handle expiration (preserve ISO format if present)
        if 'expires_at' in data:
            flat['expires_at'] = data['expires_at']
        elif 'expires_in' in data:
            # Keep expires_in if that's what's in the old format
            # The credential manager will handle it on first load
            flat['expires_in'] = data['expires_in']

    return flat


def is_nested_format(credential: dict[str, Any]) -> bool:
    """Check if a credential uses the old nested format.

    Args:
        credential: Credential dictionary to check

    Returns:
        True if credential has nested 'client' or 'data' fields

    """
    return 'client' in credential or 'data' in credential


def migrate_credentials_file(file_path: Path) -> None:
    """Migrate a credentials file from nested to flat format.

    Args:
        file_path: Path to credentials.json file

    """
    print(f'Reading credentials from: {file_path}')

    # Read existing file
    with file_path.open('rb') as f:
        credentials = orjson.loads(f.read())

    # Check if migration is needed
    needs_migration = any(is_nested_format(cred) for cred in credentials)

    if not needs_migration:
        print('✓ Credentials are already in flat format. No migration needed.')
        return

    print(f'Found {len(credentials)} credential(s) to migrate')

    # Migrate each credential
    migrated = [migrate_credential(cred) for cred in credentials]

    # Create backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = file_path.with_suffix(f'.backup_{timestamp}.json')

    print(f'Creating backup: {backup_path}')
    with backup_path.open('wb') as f:
        f.write(orjson.dumps(credentials, option=orjson.OPT_INDENT_2))

    # Write migrated credentials
    print(f'Writing migrated credentials to: {file_path}')
    with file_path.open('wb') as f:
        f.write(orjson.dumps(migrated, option=orjson.OPT_INDENT_2))

    print('\n✓ Migration complete!')
    print(f'  - Original file backed up to: {backup_path}')
    print(f'  - New flat format written to: {file_path}')


def main() -> None:
    """Main entry point for migration script."""
    if len(sys.argv) != 2:
        print('Usage: python scripts/migrate_credentials.py /path/to/credentials.json')
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f'Error: File not found: {file_path}')
        sys.exit(1)

    if not file_path.is_file():
        print(f'Error: Not a file: {file_path}')
        sys.exit(1)

    try:
        migrate_credentials_file(file_path)
    except Exception as e:
        print(f'\nError during migration: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
