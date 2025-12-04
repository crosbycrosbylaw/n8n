"""Unit tests for EmailProcessor.

Tests cover:
- Processor initialization with GraphClient and state
- Batch processing workflow
- Flag application logic
- Result-to-flag conversion
- Batch result calculations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal
from unittest.mock import Mock

import pytest
from rampy import test

from eserv.monitor.flags import status_flag
from eserv.monitor.processor import EmailProcessor
from eserv.monitor.types import EmailInfo, EmailRecord, ProcessedResult

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from eserv.monitor.types import ErrorDict


@pytest.fixture
def mock_pipeline() -> Mock:
    """Create mock Pipeline with config and state."""
    pipeline = Mock(spec=['config', 'state', 'execute'])

    # Mock config with credentials and monitoring
    pipeline.config = Mock()
    pipeline.config.credentials = {
        'microsoft-outlook': Mock(access_token='test_outlook_token'),
    }
    pipeline.config.monitoring = Mock()

    # Mock state tracker
    pipeline.state = Mock(spec=['processed', 'record'])
    pipeline.state.processed = set()

    return pipeline


@pytest.fixture
def mock_graph_client() -> Mock:
    """Create mock GraphClient."""
    return Mock(spec=['fetch_unprocessed_emails', 'apply_flag'])


@pytest.fixture
def sample_email_record() -> EmailRecord:
    """Create sample EmailRecord for testing."""
    return EmailRecord(
        uid='email-123',
        sender='court@example.com',
        subject='Test Case Filing',
        received_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        html_body='<html><body>Test email</body></html>',
    )


@test.paramdef('evaluator').values(
    (lambda p, mock: p.state is mock.state,),
    (lambda p, mock: p.client is not None,),
)
class TestEmailProcessorInit:
    """Test EmailProcessor initialization."""

    def test_dynamic(
        self,
        evaluator: Callable[[EmailProcessor, Mock], bool],
        mock_pipeline: Mock,
    ) -> None:
        """Test GraphClient created from pipeline config credentials."""
        processor = EmailProcessor(pipeline=mock_pipeline)

        assert evaluator(processor, mock_pipeline)


@dataclass(frozen=True, slots=True, kw_only=True)
class process_batch_scenario:
    records: Sequence[EmailRecord]
    expect_succeeded: int

    expect_total: int | None = None
    expect_called: int | None = None
    mock_execute: Callable[[EmailRecord], ProcessedResult] | None = None

    switches: set[
        Literal[
            'insert_sample',
            'verify_flags_applied',
            'verify_state_recorded',
        ]
    ] = field(default_factory=set)


@test.scenarios(
    successful_batch=process_batch_scenario(
        records=[
            EmailRecord(
                uid='email-456',
                sender='court@example.com',
                subject='Another Case',
                received_at=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
                html_body='<html><body>Email 2</body></html>',
            ),
            EmailRecord(
                uid='email-789',
                sender='court@example.com',
                subject='Third Case',
                received_at=datetime(2025, 1, 3, 12, 0, tzinfo=UTC),
                html_body='<html><body>Email 3</body></html>',
            ),
        ],
        expect_succeeded=3,
        switches={'insert_sample', 'verify_flags_applied', 'verify_state_recorded'},
    ),
    empty_batch=process_batch_scenario(
        records=[],
        expect_succeeded=0,
    ),
    partial_failures=process_batch_scenario(
        records=[
            EmailRecord(
                uid='email-456',
                sender='court@example.com',
                subject='Another Case',
                received_at=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
                html_body='<html><body>Email 2</body></html>',
            ),
            EmailRecord(
                uid='email-789',
                sender='court@example.com',
                subject='Third Case',
                received_at=datetime(2025, 1, 3, 12, 0, tzinfo=UTC),
                html_body='<html><body>Email 3</body></html>',
            ),
        ],
        mock_execute=lambda rec: ProcessedResult(
            record=EmailInfo(uid=rec.uid, sender=rec.sender, subject=rec.subject),
            error={'category': 'download', 'message': 'Network error'} if rec.uid == 'email-456' else None,
        ),
        expect_succeeded=2,
        switches={'insert_sample'},
    ),
)
class TestProcessBatch:
    """Test batch processing workflow."""

    def test_dynamic(  # noqa: PLR0913, PLR0917
        self,
        records: list[EmailRecord],
        expect_succeeded: int,
        expect_total: int | None,
        expect_called: int | None,
        mock_execute: Callable[...] | None,
        switches: set[str],
        mock_pipeline: Mock,
        sample_email_record: EmailRecord,
    ) -> None:

        if 'insert_sample' in switches:
            records.insert(0, sample_email_record)

        # Convert dict records back to EmailRecord objects (rampy serialization workaround)
        email_records = []
        for rec in records:
            if isinstance(rec, dict):
                email_records.append(EmailRecord(**rec))
            else:
                email_records.append(rec)

        mock_client = Mock(spec=['fetch_unprocessed_emails', 'apply_flag'])
        mock_client.fetch_unprocessed_emails.return_value = email_records

        processor = EmailProcessor(pipeline=mock_pipeline)
        processor.client = mock_client

        # Configure execute to return ProcessedResult objects
        if mock_execute is not None:
            # Wrap the mock_execute to handle both dict and EmailRecord
            def wrapped_execute(rec):
                # Handle dict serialization from rampy
                if isinstance(rec, dict):
                    rec_obj = EmailRecord(**rec)
                    return mock_execute(rec_obj)
                return mock_execute(rec)

            mock_pipeline.execute.side_effect = wrapped_execute
        else:
            # Default: return success ProcessedResult for all records
            def default_execute(rec):
                # Handle dict serialization from rampy
                if isinstance(rec, dict):
                    uid = rec['uid']
                    sender = rec['sender']
                    subject = rec['subject']
                else:
                    uid = rec.uid
                    sender = rec.sender
                    subject = rec.subject

                return ProcessedResult(
                    record=EmailInfo(uid=uid, sender=sender, subject=subject),
                    error=None,
                )

            mock_pipeline.execute.side_effect = default_execute

        expect_total = expect_total or len(records)
        expect_called = expect_called or expect_total

        batch_result = processor.process_batch(num_days=1)

        assert batch_result.total == expect_total
        assert batch_result.succeeded == expect_succeeded
        assert batch_result.failed == expect_total - expect_succeeded

        assert mock_pipeline.execute.call_count == expect_called

        if 'verify_flags_applied' in switches:
            assert mock_client.apply_flag.call_count == expect_called

        if 'verify_state_recorded' in switches:
            assert mock_pipeline.state.record.call_count == expect_called


def test_flag_application_failure_continues_processing(
    mock_pipeline: Mock,
    sample_email_record: EmailRecord,
) -> None:
    """Test that flag application failures don't crash processing."""
    processor = EmailProcessor(pipeline=mock_pipeline)
    mock_client = Mock(spec=['fetch_unprocessed_emails', 'apply_flag'])

    # Mock fetch returns 1 email
    mock_client.fetch_unprocessed_emails.return_value = [sample_email_record]

    # Mock execute returns success
    mock_pipeline.execute.return_value = ProcessedResult(
        record=EmailInfo(
            uid=sample_email_record.uid,
            sender=sample_email_record.sender,
            subject=sample_email_record.subject,
        ),
        error=None,
    )

    # Mock flag application raises exception
    mock_client.apply_flag.side_effect = Exception('Flag API error')
    processor.client = mock_client

    # Execute batch processing - should NOT raise
    result = processor.process_batch(num_days=1)

    # Verify processing completed despite flag failure
    assert result.total == 1
    assert result.succeeded == 1

    # Verify state still recorded
    assert mock_pipeline.state.record.call_count == 1


@test.paramdef('error').values(
    (None,),
    ({'category': 'download', 'message': 'Network timeout'},),  # pyright: ignore[reportArgumentType]
)
class TestResultFlagConversion:
    """Test result to flag conversion logic."""

    def test_dynamic(
        self,
        error: ErrorDict | None,
        mock_pipeline: Mock,
    ) -> None:
        """Test successful result converts to success flag."""
        if error is not None:
            expect_flag = status_flag(error)
        else:
            expect_flag = status_flag()

        result = ProcessedResult(
            record=EmailInfo(
                uid='email-123',
                sender='test@example.com',
                subject='Test',
            ),
            error=error,
        )

        processor = EmailProcessor(pipeline=mock_pipeline)
        assert processor._result_to_flag(result) == expect_flag


@dataclass(frozen=True, slots=True, kw_only=True)
class batch_result_scenario:
    count: int
    error: ErrorDict | None
    expect_succeeded: int


@test.scenarios(
    all_successes=batch_result_scenario(count=5, error=None, expect_succeeded=5),
    all_failures=batch_result_scenario(
        count=5,
        error={'category': 'download', 'message': 'Error'},
        expect_succeeded=0,
    ),
    mixed_results=batch_result_scenario(count=3, error=None, expect_succeeded=2),
)
class TestBatchResultSummary:
    """Test batch result count calculations."""

    def test_dynamic(
        self,
        count: int,
        error: ErrorDict | None,
        expect_succeeded: int,
    ) -> None:
        from eserv.monitor.types import BatchResult

        # Create results based on scenario
        if error is None and count == expect_succeeded:
            # All successes
            results = [
                ProcessedResult(
                    record=EmailInfo(uid=f'email-{i}', sender='test@example.com', subject='Test'),
                    error=None,
                )
                for i in range(count)
            ]
        elif expect_succeeded == 0:
            # All failures
            results = [
                ProcessedResult(
                    record=EmailInfo(uid=f'email-{i}', sender='test@example.com', subject='Test'),
                    error=error,
                )
                for i in range(count)
            ]
        else:
            # Mixed: create expect_succeeded successes and (count - expect_succeeded) failures
            results = []
            for i in range(count):
                results.append(
                    ProcessedResult(
                        record=EmailInfo(uid=f'email-{i}', sender='test@example.com', subject='Test'),
                        error=None if i < expect_succeeded else {'category': 'download', 'message': 'Error'},
                    )
                )

        batch_result = BatchResult(results)

        assert batch_result.total == (batch_size := len(results))
        assert batch_result.succeeded == expect_succeeded
        assert batch_result.failed == batch_size - expect_succeeded
