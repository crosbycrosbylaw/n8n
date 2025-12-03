"""Integration tests for eserv upload pipeline workflow.

Tests the complete pipeline workflow combining multiple components.
For individual component tests, see tests/eserv/util/test_*.py

Run with: pytest tests/test_integration.py -v
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rampy import test

from eserv.util.configuration import Config
from eserv.util.email_state import EmailState, hash_email_subject
from eserv.util.error_tracking import ErrorTracker, PipelineStage
from eserv.util.index_cache import IndexCache
from eserv.util.target_finder import FolderMatcher

if TYPE_CHECKING:
    from typing import Any


def workflow_scenario(
    *,
    case_name: str = 'Smith v. Jones',
    has_folder_match: bool = True,
    is_duplicate: bool = False,
) -> dict[str, Any]:
    """Create integration test scenario for full workflow."""
    folders = ['Smith v. Jones', 'Doe Corporation'] if has_folder_match else ['Different Case']

    return {
        'params': [case_name, folders, is_duplicate],
        'exception': None,
    }


@test.scenarios(**{
    'successful upload workflow': workflow_scenario(
        case_name='Smith v. Jones',
        has_folder_match=True,
    ),
    'manual review workflow': workflow_scenario(
        case_name='Unknown Case',
        has_folder_match=False,
    ),
    'duplicate email workflow': workflow_scenario(
        case_name='Smith v. Jones',
        has_folder_match=True,
        is_duplicate=True,
    ),
})
class TestUploadWorkflow:
    """Test complete upload workflow integrating multiple components."""

    def test(self, /, params: list[Any], exception: type[Exception] | None):
        def execute() -> None:
            case_name, folders, is_duplicate = params
            temp_dir = Path(tempfile.mkdtemp())

            try:
                # Initialize components
                state_file = temp_dir / 'email_state.json'
                error_log = temp_dir / 'error_log.json'
                cache_file = temp_dir / 'dbx_index.json'

                email_state = EmailState(state_file=state_file)
                error_tracker = ErrorTracker(log_file=error_log)
                index_cache = IndexCache(cache_file=cache_file, ttl_hours=4)

                # Populate cache with folders
                folder_index = {
                    folder: {'id': f'id_{i}', 'name': folder} for i, folder in enumerate(folders)
                }
                index_cache.refresh(folder_index)

                # Simulate duplicate email if requested
                if is_duplicate:
                    email_state.mark_processed(case_name, matched_folder='/Test')

                # Check if already processed
                if email_state.is_processed(case_name):
                    # Should skip processing
                    return

                # Try to match folder
                matcher = FolderMatcher(folder_paths=folders, min_score=50.0)
                match = matcher.find_best_match(case_name)

                email_hash = hash_email_subject(case_name)

                if match:
                    # Success path
                    email_state.mark_processed(case_name, matched_folder=match.folder_path)
                    assert email_state.is_processed(case_name)
                    assert email_state.get_matched_folder(case_name) == match.folder_path

                else:
                    # Manual review path
                    email_state.mark_processed(case_name, matched_folder=None)
                    error_tracker.log_error(
                        email_hash=email_hash,
                        stage=PipelineStage.FOLDER_MATCHING,
                        error_message='No folder match found',
                    )

                    # Verify error was logged
                    errors = error_tracker.get_errors_for_email(email_hash)
                    assert len(errors) >= 1

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()


@test.scenarios(**{
    'config loads successfully': {'params': []},
})
class TestEnvironmentSetup:
    """Test that environment configuration is properly set up."""

    def test(self, /, params: list[Any]):
        config = Config.from_env()

        # Verify all components are configured
        assert config.smtp.server
        assert config.dropbox.token
        assert config.paths.service_dir.exists()
        assert config.cache.ttl_hours > 0
