"""Unit tests for EmailProcessor.

Tests cover:
- Processor initialization with GraphClient and state
- Batch processing workflow
- Flag application logic
- Result-to-flag conversion
- Batch result calculations
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from eserv.monitor.processor import EmailProcessor
from eserv.monitor.types import EmailInfo, EmailRecord, ProcessedResult

if TYPE_CHECKING:
    from eserv.monitor.flags import StatusFlag


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


class TestEmailProcessorInit:
    """Test EmailProcessor initialization."""

    def test_post_init_creates_graph_client(self, mock_pipeline: Mock) -> None:
        """Test GraphClient created from pipeline config credentials."""
        processor = EmailProcessor(pipeline=mock_pipeline)

        # Verify GraphClient initialized
        assert hasattr(processor, 'client')
        assert processor.client is not None

    def test_post_init_copies_state_from_pipeline(self, mock_pipeline: Mock) -> None:
        """Test state copied from pipeline state tracker."""
        processor = EmailProcessor(pipeline=mock_pipeline)

        # Verify state is same as pipeline.state
        assert processor.state is mock_pipeline.state


class TestProcessBatch:
    """Test batch processing workflow."""

    def test_successful_batch_processing(
        self,
        mock_pipeline: Mock,
        sample_email_record: EmailRecord,
    ) -> None:
        """Test successful processing of multiple emails."""
        # Setup processor with mocked client
        processor = EmailProcessor(pipeline=mock_pipeline)
        mock_client = Mock(spec=['fetch_unprocessed_emails', 'apply_flag'])

        # Mock fetch returns 3 emails
        email1 = sample_email_record
        email2 = EmailRecord(
            uid='email-456',
            sender='court@example.com',
            subject='Another Case',
            received_at=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
            html_body='<html><body>Email 2</body></html>',
        )
        email3 = EmailRecord(
            uid='email-789',
            sender='court@example.com',
            subject='Third Case',
            received_at=datetime(2025, 1, 3, 12, 0, tzinfo=UTC),
            html_body='<html><body>Email 3</body></html>',
        )
        mock_client.fetch_unprocessed_emails.return_value = [email1, email2, email3]

        # Mock execute returns success results
        def mock_execute(record: EmailRecord) -> ProcessedResult:
            return ProcessedResult(
                record=EmailInfo(uid=record.uid, sender=record.sender, subject=record.subject),
                error=None,
            )

        mock_pipeline.execute.side_effect = mock_execute
        processor.client = mock_client

        # Execute batch processing
        result = processor.process_batch(num_days=1)

        # Verify results
        assert result.total == 3
        assert result.succeeded == 3
        assert result.failed == 0
        assert len(result.results) == 3

        # Verify execute called for each email
        assert mock_pipeline.execute.call_count == 3

        # Verify flags applied
        assert mock_client.apply_flag.call_count == 3

        # Verify state recorded
        assert mock_pipeline.state.record.call_count == 3

    def test_empty_batch(self, mock_pipeline: Mock) -> None:
        """Test processing when no unprocessed emails exist."""
        processor = EmailProcessor(pipeline=mock_pipeline)
        mock_client = Mock(spec=['fetch_unprocessed_emails', 'apply_flag'])

        # Mock fetch returns empty list
        mock_client.fetch_unprocessed_emails.return_value = []
        processor.client = mock_client

        # Execute batch processing
        result = processor.process_batch(num_days=1)

        # Verify results
        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert len(result.results) == 0

        # Verify no execute calls
        assert mock_pipeline.execute.call_count == 0

    def test_partial_failures(
        self,
        mock_pipeline: Mock,
        sample_email_record: EmailRecord,
    ) -> None:
        """Test batch processing with some failures."""
        processor = EmailProcessor(pipeline=mock_pipeline)
        mock_client = Mock(spec=['fetch_unprocessed_emails', 'apply_flag'])

        # Mock fetch returns 3 emails
        email1 = sample_email_record
        email2 = EmailRecord(
            uid='email-456',
            sender='court@example.com',
            subject='Another Case',
            received_at=datetime(2025, 1, 2, 12, 0, tzinfo=UTC),
            html_body='<html><body>Email 2</body></html>',
        )
        email3 = EmailRecord(
            uid='email-789',
            sender='court@example.com',
            subject='Third Case',
            received_at=datetime(2025, 1, 3, 12, 0, tzinfo=UTC),
            html_body='<html><body>Email 3</body></html>',
        )
        mock_client.fetch_unprocessed_emails.return_value = [email1, email2, email3]

        # Mock execute returns mixed results (success, error, success)
        def mock_execute(record: EmailRecord) -> ProcessedResult:
            error = (
                {'category': 'download', 'message': 'Network error'}
                if record.uid == 'email-456'
                else None
            )
            return ProcessedResult(
                record=EmailInfo(uid=record.uid, sender=record.sender, subject=record.subject),
                error=error,
            )

        mock_pipeline.execute.side_effect = mock_execute
        processor.client = mock_client

        # Execute batch processing
        result = processor.process_batch(num_days=1)

        # Verify results
        assert result.total == 3
        assert result.succeeded == 2
        assert result.failed == 1
        assert len(result.results) == 3

    def test_flag_application_failure_continues_processing(
        self,
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


class TestResultToFlag:
    """Test result to flag conversion logic."""

    def test_successful_result_returns_success_flag(self, mock_pipeline: Mock) -> None:
        """Test successful result converts to success flag."""
        processor = EmailProcessor(pipeline=mock_pipeline)

        # Create success result
        result = ProcessedResult(
            record=EmailInfo(uid='email-123', sender='test@example.com', subject='Test'),
            error=None,
        )

        # Convert to flag
        flag = processor._result_to_flag(result)

        # Verify flag indicates success (no error field in flag)
        assert flag is not None
        assert isinstance(flag, dict)

    def test_error_result_returns_error_flag(self, mock_pipeline: Mock) -> None:
        """Test error result converts to error flag with exception string."""
        processor = EmailProcessor(pipeline=mock_pipeline)

        # Create error result
        error_info = {'category': 'download', 'message': 'Network timeout'}
        result = ProcessedResult(
            record=EmailInfo(uid='email-123', sender='test@example.com', subject='Test'),
            error=error_info,
        )

        # Convert to flag
        flag = processor._result_to_flag(result)

        # Verify flag indicates error
        assert flag is not None
        assert isinstance(flag, dict)


class TestBatchResultSummary:
    """Test batch result count calculations."""

    def test_all_successes(self) -> None:
        """Test batch with all successful results."""
        results = [
            ProcessedResult(
                record=EmailInfo(uid=f'email-{i}', sender='test@example.com', subject='Test'),
                error=None,
            )
            for i in range(5)
        ]

        # Import BatchResult to create instance
        from eserv.monitor.types import BatchResult

        batch_result = BatchResult(total=5, succeeded=5, failed=0, results=results)

        assert batch_result.total == 5
        assert batch_result.succeeded == 5
        assert batch_result.failed == 0

    def test_all_failures(self) -> None:
        """Test batch with all failed results."""
        results = [
            ProcessedResult(
                record=EmailInfo(uid=f'email-{i}', sender='test@example.com', subject='Test'),
                error={'category': 'download', 'message': 'Error'},
            )
            for i in range(5)
        ]

        from eserv.monitor.types import BatchResult

        batch_result = BatchResult(total=5, succeeded=0, failed=5, results=results)

        assert batch_result.total == 5
        assert batch_result.succeeded == 0
        assert batch_result.failed == 5

    def test_mixed_results(self) -> None:
        """Test batch with mixed success/failure results."""
        results = [
            ProcessedResult(
                record=EmailInfo(uid='email-1', sender='test@example.com', subject='Test'),
                error=None,
            ),
            ProcessedResult(
                record=EmailInfo(uid='email-2', sender='test@example.com', subject='Test'),
                error={'category': 'download', 'message': 'Error'},
            ),
            ProcessedResult(
                record=EmailInfo(uid='email-3', sender='test@example.com', subject='Test'),
                error=None,
            ),
        ]

        from eserv.monitor.types import BatchResult

        batch_result = BatchResult(total=3, succeeded=2, failed=1, results=results)

        assert batch_result.total == 3
        assert batch_result.succeeded == 2
        assert batch_result.failed == 1
