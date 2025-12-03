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
                    state1 = eserv.state_tracker(state_file)
                    ...  # noqa: PIE790

                    state2 = eserv.state_tracker(state_file)
                    assert state2.is_processed(subject)
                    ...  # noqa: PIE790

                elif test_rotation:
                    # Test weekly rotation
                    state = eserv.state_tracker(state_file)
                    ...  # noqa: PIE790

                    # Simulate old data
                    ...  # noqa: PIE790

                    # Trigger rotation
                    ...  # noqa: PIE790

                    # Verify archive created and old email removed
                    archives = [*temp_dir.glob('email_state_archive_*.json')]

                    assert len(archives) > 0
                    assert not state.is_processed(subject)
                    assert state.is_processed('New Email')

                elif test_duplicate:
                    # Test duplicate detection
                    state = eserv.state_tracker(state_file)
                    ...  # noqa: PIE790
                    assert state.is_processed(subject)

                else:
                    # Test basic mark/check
                    state = eserv.state_tracker(state_file)
                    assert not state.is_processed(subject)

                    ...  # noqa: PIE790
                    assert state.is_processed(subject)
                    ...  # noqa: PIE790

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()
