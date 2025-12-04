"""Unit tests for core Pipeline orchestration.

Tests cover:
- Pipeline initialization with config, state, and error tracker
- Complete processing workflow through all 6 stages
- Stage transition error handling
- Duplicate detection via state tracking
- Upload result status routing (SUCCESS, MANUAL_REVIEW, ERROR, NO_WORK)
- Monitor workflow and error cleanup
- Execute wrapper with exception handling
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from eserv.core import Pipeline
from eserv.errors import PipelineError
from eserv.stages import status
from eserv.stages.types import UploadResult

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_dotenv_path(tempdir) -> Path:
    """Create mock .env file path."""
    env_path = tempdir / '.env'
    env_path.write_text('TEST_VAR=test_value\n')
    return env_path


@pytest.fixture
def mock_dependencies():
    """Mock all Pipeline dependencies."""
    mock_config = Mock()
    mock_config.state = Mock(state_file=Path('/tmp/state.json'))
    mock_config.paths = Mock(service_dir=Path('/tmp'))

    mock_state = Mock(spec=['is_processed', 'processed'])
    mock_state.is_processed.return_value = False
    mock_state.processed = set()

    mock_tracker = Mock(spec=['track', 'clear_old_errors'])
    mock_track_cm = Mock()
    mock_track_cm.__enter__ = Mock(return_value=mock_track_cm)
    mock_track_cm.__exit__ = Mock(return_value=None)

    # Configure error() to raise PipelineError when raises=True
    def mock_error(message, stage, context=None, raises=None):
        if raises:
            from eserv.errors._core import PipelineError

            raise PipelineError(message=message, stage=stage)

    mock_track_cm.error = Mock(side_effect=mock_error)
    mock_track_cm.warning = Mock()
    mock_tracker.track.return_value = mock_track_cm

    return {
        'config': mock_config,
        'state': mock_state,
        'tracker': mock_tracker,
        'track_cm': mock_track_cm,
    }


@pytest.fixture
def sample_email_record():
    """Create sample EmailRecord for testing."""
    from eserv.monitor.types import EmailRecord

    return EmailRecord(
        uid='email-123',
        sender='court@example.com',
        subject='Smith v. Jones - Filing Accepted',
        received_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        html_body='<html><body><a href="http://example.com/doc.pdf">Download</a></body></html>',
    )


class TestPipelineInit:
    """Test Pipeline initialization."""

    def test_config_loading_from_dotenv_path(
        self,
        mock_dotenv_path: Path,
        mock_dependencies: dict,
    ) -> None:
        """Test config loaded from .env path."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']) as mock_config_fn:
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    # Initialize pipeline with dotenv path
                    pipeline = Pipeline(dotenv_path=mock_dotenv_path)

                    # Verify config called with path
                    mock_config_fn.assert_called_once_with(mock_dotenv_path)

                    # Verify pipeline attributes set
                    assert pipeline.config is mock_dependencies['config']

    def test_state_tracker_initialization(self, mock_dependencies: dict) -> None:
        """Test state tracker initialized from config."""
        with (
            patch('eserv.core.config', return_value=mock_dependencies['config']),
            patch(
                'eserv.core.state_tracker',
                return_value=mock_dependencies['state'],
            ) as mock_state_fn,
            patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']),
        ):
            # Initialize pipeline
            pipeline = Pipeline()

            # Verify state_tracker called with state file path
            mock_state_fn.assert_called_once_with(Path('/tmp/state.json'))

            # Verify pipeline.state set
            assert pipeline.state is mock_dependencies['state']

    def test_error_tracker_initialization(self, mock_dependencies: dict) -> None:
        """Test error tracker initialized from config."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch(
                    'eserv.core.error_tracker',
                    return_value=mock_dependencies['tracker'],
                ) as mock_tracker_fn:
                    # Initialize pipeline
                    pipeline = Pipeline()

                    # Verify error_tracker called with error log path
                    expected_path = Path('/tmp') / 'error_log.json'
                    mock_tracker_fn.assert_called_once_with(expected_path)

                    # Verify pipeline.tracker set
                    assert pipeline.tracker is mock_dependencies['tracker']


class TestPipelineProcess:
    """Test Pipeline.process() complete workflow."""

    def test_successful_complete_workflow(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test successful processing through all 6 stages."""
        # Setup temp store path
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)
        pdf_path = store_path / 'Motion.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\nTest PDF')

        # Mock all stage functions
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup') as mock_soup_class:
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                with patch('eserv.core.upload_documents') as mock_upload:
                                    # Setup mocks
                                    mock_soup = Mock()
                                    mock_soup_class.return_value = mock_soup

                                    mock_extract.return_value = Mock(
                                        case_name='Smith v. Jones',
                                        doc_count=1,
                                    )

                                    mock_upload.return_value = UploadResult(
                                        status=status.SUCCESS,
                                        folder_path='/Clio/Smith v. Jones',
                                        uploaded_files=['Motion.pdf'],
                                    )

                                    # Initialize pipeline and process
                                    pipeline = Pipeline()
                                    result = pipeline.process(sample_email_record)

                                    # Verify result
                                    assert result.status == status.SUCCESS
                                    assert result.folder_path == '/Clio/Smith v. Jones'

                                    # Verify all stages called
                                    mock_soup_class.assert_called_once()
                                    mock_extract.assert_called_once()
                                    mock_upload.assert_called_once()

    def test_html_parsing_failure(
        self,
        mock_dependencies: dict,
        sample_email_record,
    ) -> None:
        """Test HTML parsing failure raises PipelineError."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch(
                        'eserv.core.BeautifulSoup',
                        side_effect=Exception('Parse error'),
                    ):
                        # Initialize pipeline
                        pipeline = Pipeline()

                        # Process should raise PipelineError
                        with pytest.raises(PipelineError):
                            pipeline.process(sample_email_record)

                        # Verify error logged
                        mock_dependencies['track_cm'].error.assert_called_once()

    def test_download_failure(
        self,
        mock_dependencies: dict,
        sample_email_record,
    ) -> None:
        """Test document download failure raises PipelineError."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch(
                            'eserv.core.download_documents',
                            side_effect=Exception('Download error'),
                        ):
                            # Initialize pipeline
                            pipeline = Pipeline()

                            # Process should raise PipelineError
                            with pytest.raises(PipelineError):
                                pipeline.process(sample_email_record)

                            # Verify error logged
                            mock_dependencies['track_cm'].error.assert_called_once()

    def test_upload_info_extraction_failure(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test upload info extraction failure raises PipelineError."""
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch(
                                'eserv.core.extract_upload_info',
                                side_effect=Exception('Extraction error'),
                            ):
                                # Initialize pipeline
                                pipeline = Pipeline()

                                # Process should raise PipelineError
                                with pytest.raises(PipelineError):
                                    pipeline.process(sample_email_record)

                                # Verify error logged
                                mock_dependencies['track_cm'].error.assert_called_once()

    def test_duplicate_detection_uid_already_processed(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test duplicate email detection via state tracker."""
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)

        # Mock state to return True for is_processed
        mock_dependencies['state'].is_processed.return_value = True

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                mock_extract.return_value = Mock(case_name='Smith v. Jones')

                                # Initialize pipeline
                                pipeline = Pipeline()
                                result = pipeline.process(sample_email_record)

                                # Verify NO_WORK returned
                                assert result.status == status.NO_WORK

                                # Verify is_processed checked
                                mock_dependencies['state'].is_processed.assert_called_once_with('email-123')

    def test_no_pdfs_after_download(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test NO_WORK when no PDF files after download."""
        # Empty store directory (no PDFs)
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                with patch('eserv.core.upload_documents') as mock_upload:
                                    mock_extract.return_value = Mock(case_name='Smith v. Jones')
                                    mock_upload.return_value = UploadResult(status=status.NO_WORK)

                                    # Initialize pipeline
                                    pipeline = Pipeline()
                                    result = pipeline.process(sample_email_record)

                                    # Verify NO_WORK status
                                    assert result.status == status.NO_WORK

    def test_upload_success_status(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test SUCCESS status from successful upload."""
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)
        pdf_path = store_path / 'Motion.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\nTest')

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                with patch('eserv.core.upload_documents') as mock_upload:
                                    mock_extract.return_value = Mock(case_name='Smith v. Jones')
                                    mock_upload.return_value = UploadResult(
                                        status=status.SUCCESS,
                                        folder_path='/Clio/Smith v. Jones',
                                        uploaded_files=['Motion.pdf'],
                                    )

                                    # Initialize pipeline
                                    pipeline = Pipeline()
                                    result = pipeline.process(sample_email_record)

                                    # Verify SUCCESS status
                                    assert result.status == status.SUCCESS

    def test_upload_manual_review_status(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test MANUAL_REVIEW status when no folder match."""
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)
        pdf_path = store_path / 'Motion.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\nTest')

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                with patch('eserv.core.upload_documents') as mock_upload:
                                    mock_extract.return_value = Mock(case_name='Unknown Case')
                                    mock_upload.return_value = UploadResult(
                                        status=status.MANUAL_REVIEW,
                                        folder_path='/Clio/Manual Review/',
                                        uploaded_files=['Motion.pdf'],
                                    )

                                    # Initialize pipeline
                                    pipeline = Pipeline()
                                    result = pipeline.process(sample_email_record)

                                    # Verify MANUAL_REVIEW status
                                    assert result.status == status.MANUAL_REVIEW

                                    # Verify warning logged
                                    mock_dependencies['track_cm'].warning.assert_called_once()

    def test_upload_error_status(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test ERROR status from upload failure."""
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)
        pdf_path = store_path / 'Motion.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\nTest')

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                with patch('eserv.core.upload_documents') as mock_upload:
                                    mock_extract.return_value = Mock(case_name='Smith v. Jones')
                                    mock_upload.return_value = UploadResult(
                                        status=status.ERROR,
                                        error='Dropbox API error',
                                    )

                                    # Initialize pipeline
                                    pipeline = Pipeline()

                                    # Process should raise PipelineError
                                    with pytest.raises(PipelineError):
                                        pipeline.process(sample_email_record)

                                    # Verify error logged
                                    mock_dependencies['track_cm'].error.assert_called_once()


class TestPipelineMonitor:
    """Test Pipeline.monitor() workflow."""

    def test_batch_processing_via_email_processor(self, mock_dependencies: dict) -> None:
        """Test monitor delegates to EmailProcessor."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.EmailProcessor') as mock_processor_class:
                        # Mock EmailProcessor.process_batch
                        mock_processor = Mock()
                        mock_batch_result = Mock(total=5, succeeded=4, failed=1)
                        mock_processor.process_batch.return_value = mock_batch_result
                        mock_processor_class.return_value = mock_processor

                        # Initialize pipeline and monitor
                        pipeline = Pipeline()
                        result = pipeline.monitor(num_days=1)

                        # Verify EmailProcessor created with pipeline
                        mock_processor_class.assert_called_once_with(pipeline)

                        # Verify process_batch called
                        mock_processor.process_batch.assert_called_once_with(1)

                        # Verify result returned
                        assert result is mock_batch_result

    def test_error_log_cleanup_before_processing(self, mock_dependencies: dict) -> None:
        """Test error log cleanup called before monitoring."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.EmailProcessor') as mock_processor_class:
                        mock_processor = Mock()
                        mock_processor.process_batch.return_value = Mock()
                        mock_processor_class.return_value = mock_processor

                        # Initialize pipeline and monitor
                        pipeline = Pipeline()
                        pipeline.monitor(num_days=1)

                        # Verify error cleanup called
                        mock_dependencies['tracker'].clear_old_errors.assert_called_once_with(days=30)


class TestPipelineExecute:
    """Test Pipeline.execute() wrapper."""

    def test_successful_execution_wrapper(
        self,
        mock_dependencies: dict,
        sample_email_record,
        tempdir,
    ) -> None:
        """Test execute wraps process() successfully."""
        store_path = tempdir / 'docs'
        store_path.mkdir(exist_ok=True)
        pdf_path = store_path / 'Motion.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\nTest')

        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup'):
                        with patch('eserv.core.download_documents', return_value=('Motion', store_path)):
                            with patch('eserv.core.extract_upload_info') as mock_extract:
                                with patch('eserv.core.upload_documents') as mock_upload:
                                    mock_extract.return_value = Mock(case_name='Smith v. Jones')
                                    mock_upload.return_value = UploadResult(status=status.SUCCESS)

                                    # Initialize pipeline and execute
                                    pipeline = Pipeline()
                                    result = pipeline.execute(sample_email_record)

                                    # Verify ProcessedResult returned
                                    assert result.error is None
                                    assert result.status == 'success'

    def test_pipeline_error_converted_to_processed_result(
        self,
        mock_dependencies: dict,
        sample_email_record,
    ) -> None:
        """Test PipelineError converted to ProcessedResult with error."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup', side_effect=Exception('Parse error')):
                        # Initialize pipeline
                        pipeline = Pipeline()
                        result = pipeline.execute(sample_email_record)

                        # Verify ProcessedResult with error returned
                        assert result.error is not None
                        assert result.status == 'error'

    def test_generic_exception_converted_to_processed_result(
        self,
        mock_dependencies: dict,
        sample_email_record,
    ) -> None:
        """Test generic exception converted to ProcessedResult with stage info."""
        with patch('eserv.core.config', return_value=mock_dependencies['config']):
            with patch('eserv.core.state_tracker', return_value=mock_dependencies['state']):
                with patch('eserv.core.error_tracker', return_value=mock_dependencies['tracker']):
                    with patch('eserv.core.BeautifulSoup', side_effect=RuntimeError('Unexpected error')):
                        # Initialize pipeline
                        pipeline = Pipeline()
                        result = pipeline.execute(sample_email_record)

                        # Verify ProcessedResult with error
                        # Error is wrapped in PipelineError with stage 'parsing'
                        assert result.error is not None
                        assert result.error['category'] == 'parsing'
                        assert 'message' in result.error
                        message = result.error['message']
                        assert isinstance(message, str)
                        assert 'Unexpected error' in message
