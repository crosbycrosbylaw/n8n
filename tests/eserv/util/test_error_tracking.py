"""Test suite for util/error_tracking.py pipeline error logging."""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from rampy import test

import eserv
from eserv.types import EmailRecord

if TYPE_CHECKING:
    from pathlib import Path
    from typing import TypedDict

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


def _make_record(uid: str, subject: str) -> EmailRecord:
    """Create test EmailRecord."""
    from datetime import UTC, datetime

    return EmailRecord(
        uid=uid,
        sender='court@example.com',
        subject=subject,
        received_at=datetime.now(UTC),
        html_body='<html>test</html>',
    )


@test.scenarios(
    basic_logging=scenario(
        record=_make_record('test-basic-123', 'Basic Test'),
        stage=eserv.stage.EMAIL_PARSING,
        error_message='Test parse error',
        test_persistence=False,
        test_retrieval=False,
    ),
    persistence_across_instances=scenario(
        record=_make_record('test-persist-456', 'Persistence Test'),
        stage=eserv.stage.DOCUMENT_DOWNLOAD,
        error_message='Test download error',
        test_persistence=True,
        test_retrieval=False,
    ),
    error_retrieval_by_stage=scenario(
        record=_make_record('test-retrieval-789', 'Retrieval Test'),
        stage=eserv.stage.DROPBOX_UPLOAD,
        error_message='Test upload error',
        test_persistence=False,
        test_retrieval=True,
    ),
)
class TestErrorTracker:
    def test(  # noqa: PLR0917
        self,
        /,
        record: EmailRecord,
        stage: eserv.stage,
        error_message: str,
        test_persistence: bool,
        test_retrieval: bool,
        tempdir: Path,
    ):
        log_file = tempdir / 'error_log.json'

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
