"""Test suite for util/email_state.py email processing state tracking."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rampy import test

import eserv

if TYPE_CHECKING:
    from typing import Any


def scenario(
    *,
    subject: str = 'Test Email',
    matched_folder: str | None = '/Test/Folder',
    test_duplicate: bool = False,
    test_rotation: bool = False,
    test_persistence: bool = False,
) -> dict[str, Any]:
    """Create test scenario for EmailState."""
    return {
        'params': [subject, matched_folder],
        'test_duplicate': test_duplicate,
        'test_rotation': test_rotation,
        'test_persistence': test_persistence,
    }


@test.scenarios(**{
    'mark and check processed': scenario(subject='Case 123'),
    'duplicate detection': scenario(subject='Duplicate Test', test_duplicate=True),
    'weekly rotation': scenario(subject='Old Email', test_rotation=True),
    'persistence': scenario(subject='Persist Test', test_persistence=True),
})
class TestEmailState:
    def test(
        self,
        /,
        params: list[Any],
        test_duplicate: bool,
        test_rotation: bool,
        test_persistence: bool,
    ):
        temp_dir = Path(tempfile.mkdtemp())
        try:
            subject, _ = params
            state_file = temp_dir / 'email_state.json'

            if test_persistence:
                # Test persistence across instances
                from datetime import UTC, datetime

                from eserv.monitor.types import EmailRecord

                state1 = eserv.state_tracker(state_file)
                record = EmailRecord(
                    uid='test-uid-123',
                    sender='court@example.com',
                    subject=subject,
                    received_at=datetime.now(UTC),
                    html_body='<html>test</html>',
                )
                state1.record(record)

                # Create new instance and verify persistence
                state2 = eserv.state_tracker(state_file)
                assert state2.is_processed('test-uid-123')
                assert 'test-uid-123' in state2.processed

            elif test_rotation:
                # NOTE: Weekly rotation feature was removed (see CLAUDE.md)
                # This test is skipped as the functionality no longer exists
                # The current implementation uses a fresh start approach with UID primary keys
                pytest.skip('Rotation feature removed - using fresh start approach')

            elif test_duplicate:
                # Test duplicate detection
                from datetime import UTC, datetime

                from eserv.monitor.types import EmailRecord

                state = eserv.state_tracker(state_file)
                record = EmailRecord(
                    uid='duplicate-test-456',
                    sender='court@example.com',
                    subject=subject,
                    received_at=datetime.now(UTC),
                    html_body='<html>test</html>',
                )

                # Record twice
                state.record(record)
                state.record(record)

                # Should still only be processed once
                assert state.is_processed('duplicate-test-456')
                assert len(state.processed) == 1

            else:
                # Test basic mark/check
                from datetime import UTC, datetime

                from eserv.monitor.types import EmailRecord

                state = eserv.state_tracker(state_file)
                assert not state.is_processed('basic-test-789')

                record = EmailRecord(
                    uid='basic-test-789',
                    sender='court@example.com',
                    subject=subject,
                    received_at=datetime.now(UTC),
                    html_body='<html>test</html>',
                )
                state.record(record)

                assert state.is_processed('basic-test-789')
                assert 'basic-test-789' in state.processed

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
