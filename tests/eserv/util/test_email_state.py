"""Test suite for util/email_state.py email processing state tracking."""

from __future__ import annotations

import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rampy import test

from eserv.util.email_state import EmailState

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
        'exception': None,
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
        exception: type[Exception] | None,
    ):
        def execute() -> None:
            temp_dir = Path(tempfile.mkdtemp())
            try:
                subject, matched_folder = params
                state_file = temp_dir / 'email_state.json'

                if test_persistence:
                    # Test persistence across instances
                    state1 = EmailState(state_file=state_file)
                    state1.mark_processed(subject, matched_folder=matched_folder)

                    state2 = EmailState(state_file=state_file)
                    assert state2.is_processed(subject)
                    assert state2.get_matched_folder(subject) == matched_folder

                elif test_rotation:
                    # Test weekly rotation
                    state = EmailState(state_file=state_file)
                    state.mark_processed(subject, matched_folder=matched_folder)

                    # Simulate old data
                    state._week_start = datetime.now(UTC) - timedelta(days=8)
                    assert state._should_rotate()

                    # Trigger rotation
                    state.mark_processed('New Email', matched_folder='/New')

                    # Verify archive created and old email removed
                    archives = list(temp_dir.glob('email_state_archive_*.json'))
                    assert len(archives) > 0
                    assert not state.is_processed(subject)
                    assert state.is_processed('New Email')

                elif test_duplicate:
                    # Test duplicate detection
                    state = EmailState(state_file=state_file)
                    state.mark_processed(subject, matched_folder=matched_folder)
                    assert state.is_processed(subject)

                else:
                    # Test basic mark/check
                    state = EmailState(state_file=state_file)
                    assert not state.is_processed(subject)

                    state.mark_processed(subject, matched_folder=matched_folder)
                    assert state.is_processed(subject)
                    assert state.get_matched_folder(subject) == matched_folder

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()


@test.scenarios(**{
    'hash consistency': {'subject': 'Test Subject'},
    'hash uniqueness': {'subject': 'Different Subject'},
})
class TestHashEmailSubject:
    def test(self, /, subject: str):
        hash1 = hash_email_subject(subject)
        hash2 = hash_email_subject(subject)

        # Should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 16

        # Different subjects should produce different hashes
        if subject == 'Different Subject':
            other_hash = hash_email_subject('Another Subject')
            assert hash1 != other_hash
