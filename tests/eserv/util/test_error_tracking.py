"""Test suite for util/error_tracking.py pipeline error logging."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Unpack

from rampy import test

import eserv

if TYPE_CHECKING:
    from typing import TypedDict

    from eserv.types import EmailRecord

    class Scenario(TypedDict):
        record: EmailRecord
        stage: eserv.stage
        error_message: str
        test_persistence: bool
        test_retrieval: bool


def scenario(**kwds: Unpack[Scenario]) -> Scenario:
    """Create test scenario for ErrorTracker."""
    kwds.setdefault('stage', eserv.stage.EMAIL_PARSING)
    kwds.setdefault('error_message', 'test error')
    kwds.setdefault('test_persistence', False)
    kwds.setdefault('test_retrieval', False)
    return kwds


@test.scenarios(
    # todo
)
class TestErrorTracker:
    def test(
        self,
        /,
        record: EmailRecord,
        stage: eserv.stage,
        error_message: str,
        test_persistence: bool,
        test_retrieval: bool,
    ):
        temp_dir = Path(tempfile.mkdtemp())
        try:
            log_file = temp_dir / 'error_log.json'

            if test_persistence:
                # Test persistence across instances
                tracker1 = eserv.error_tracker(log_file, record.uid)
                tracker1.error(error_message, stage)

                errors = eserv.error_tracker(log_file).get_errors_for_email(record.uid)

                assert len(errors) == 1
                assert errors[0]['error'] == error_message

                with eserv.error_tracker(log_file).track(record.uid) as tracker3:
                    tracker3.error(error_message, stage)

                errors = eserv.error_tracker(log_file).get_errors_for_email(record.uid)

                assert len(errors) > 1
                assert errors[1]['error'] == error_message

            elif test_retrieval:
                expected_count = 2

                # Test error retrieval by email and stage
                with eserv.error_tracker(log_file).track(record.uid) as tracker:
                    tracker.error(error_message, stage)
                    tracker.error('parse error', eserv.stage.EMAIL_PARSING)

                # Retrieve by email
                email_errors = tracker.get_errors_for_email(record.uid)
                assert len(email_errors) == expected_count

                # Retrieve by stage
                stage_errors = tracker.get_errors_by_stage(stage)
                assert len(stage_errors) >= 1

            else:
                # Test basic logging
                tracker = eserv.error_tracker(log_file, record.uid)
                tracker.error(error_message, stage=stage, context={'test': 'value'})

                errors = tracker.get_errors_for_email(record.uid)
                assert len(errors) == 1
                assert errors[0]['stage'] == stage.value
                assert errors[0]['error'] == error_message

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
