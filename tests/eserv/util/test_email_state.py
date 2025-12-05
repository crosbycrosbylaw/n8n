"""Test suite for util/email_state.py email processing state tracking."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

import eserv
from eserv.monitor.types import EmailRecord

if TYPE_CHECKING:
    from pathlib import Path


def create_test_record(uid: str, subject: str) -> EmailRecord:
    """Create test EmailRecord."""
    return EmailRecord(
        uid=uid,
        sender='court@example.com',
        subject=subject,
        received_at=datetime.now(UTC),
        html_body='<html>test</html>',
    )


class TestEmailStateBasic:
    """Test basic email state tracking operations."""

    def test_unprocessed_uid_returns_false(self, tempdir: Path) -> None:
        """Test is_processed returns False for unprocessed UID."""
        state_file = tempdir / 'email_state.json'
        state = eserv.state_tracker(state_file)

        assert not state.is_processed('basic-test-789')

    def test_mark_and_check_processed(self, tempdir: Path) -> None:
        """Test marking UID as processed and checking status."""
        state_file = tempdir / 'email_state.json'
        state = eserv.state_tracker(state_file)

        record = create_test_record('basic-test-789', 'Test Case')
        state.record(record)

        assert state.is_processed('basic-test-789')
        assert 'basic-test-789' in state.processed


class TestEmailStateDuplicates:
    """Test duplicate email detection."""

    def test_duplicate_recording_idempotent(self, tempdir: Path) -> None:
        """Test recording same UID twice is idempotent."""
        state_file = tempdir / 'email_state.json'
        state = eserv.state_tracker(state_file)

        record = create_test_record('duplicate-test-456', 'Duplicate Test')

        # Record twice
        state.record(record)
        state.record(record)

        # Should still only be processed once
        assert state.is_processed('duplicate-test-456')
        assert len(state.processed) == 1


class TestEmailStatePersistence:
    """Test state persistence across instances."""

    def test_state_persists_across_instances(self, tempdir: Path) -> None:
        """Test state persists when creating new tracker instance."""
        state_file = tempdir / 'email_state.json'

        # Create first instance and record email
        state1 = eserv.state_tracker(state_file)
        record = create_test_record('test-uid-123', 'Persist Test')
        state1.record(record)

        # Create new instance and verify persistence
        state2 = eserv.state_tracker(state_file)
        assert state2.is_processed('test-uid-123')
        assert 'test-uid-123' in state2.processed


class TestEmailStateRotation:
    """Test state rotation behavior."""

    def test_rotation_feature_removed(self) -> None:
        """Test that weekly rotation feature has been removed.

        NOTE: Weekly rotation feature was removed (see CLAUDE.md).
        The current implementation uses a fresh start approach with UID primary keys.
        """
        pytest.skip('Rotation feature removed - using fresh start approach')
