"""Test suite for util/error_tracking.py pipeline error logging."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from rampy import test

from eserv.util.error_tracking import ErrorTracker, PipelineStage
from eserv.util.email_state import hash_email_subject

if TYPE_CHECKING:
    from typing import Any


def scenario(
    *,
    email_hash: str = 'test_hash_123',
    stage: PipelineStage = PipelineStage.EMAIL_PARSING,
    error_message: str = 'Test error',
    test_persistence: bool = False,
    test_retrieval: bool = False,
) -> dict[str, Any]:
    """Create test scenario for ErrorTracker."""
    return {
        'params': [email_hash, stage, error_message],
        'test_persistence': test_persistence,
        'test_retrieval': test_retrieval,
        'exception': None,
    }


@test.scenarios(**{
    'log error by stage': scenario(
        email_hash=hash_email_subject('Test Error Email'),
        stage=PipelineStage.DOCUMENT_DOWNLOAD,
        error_message='Download failed',
    ),
    'error retrieval': scenario(
        email_hash=hash_email_subject('Retrieval Test'),
        stage=PipelineStage.DROPBOX_UPLOAD,
        error_message='Upload failed',
        test_retrieval=True,
    ),
    'persistence': scenario(
        email_hash=hash_email_subject('Persist Error'),
        error_message='Persist test',
        test_persistence=True,
    ),
})
class TestErrorTracker:
    def test(
        self,
        /,
        params: list[Any],
        test_persistence: bool,
        test_retrieval: bool,
        exception: type[Exception] | None,
    ):
        def execute() -> None:
            temp_dir = Path(tempfile.mkdtemp())
            try:
                email_hash, stage, error_message = params
                log_file = temp_dir / 'error_log.json'

                if test_persistence:
                    # Test persistence across instances
                    tracker1 = ErrorTracker(log_file=log_file)
                    tracker1.log_error(
                        email_hash=email_hash,
                        stage=stage,
                        error_message=error_message,
                    )

                    tracker2 = ErrorTracker(log_file=log_file)
                    errors = tracker2.get_errors_for_email(email_hash)
                    assert len(errors) == 1
                    assert errors[0]['error'] == error_message

                elif test_retrieval:
                    # Test error retrieval by email and stage
                    tracker = ErrorTracker(log_file=log_file)
                    tracker.log_error(email_hash, stage, error_message)

                    # Also log another error for different stage
                    tracker.log_error(email_hash, PipelineStage.EMAIL_PARSING, 'Parse error')

                    # Retrieve by email
                    email_errors = tracker.get_errors_for_email(email_hash)
                    assert len(email_errors) == 2

                    # Retrieve by stage
                    stage_errors = tracker.get_errors_by_stage(stage)
                    assert len(stage_errors) >= 1

                else:
                    # Test basic logging
                    tracker = ErrorTracker(log_file=log_file)
                    tracker.log_error(
                        email_hash=email_hash,
                        stage=stage,
                        error_message=error_message,
                        context={'test': 'value'},
                    )

                    errors = tracker.get_errors_for_email(email_hash)
                    assert len(errors) == 1
                    assert errors[0]['stage'] == stage.value
                    assert errors[0]['error'] == error_message

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()
