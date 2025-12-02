from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from rampy import console

from eserv.download import download_documents
from eserv.errors._core import PipelineError
from eserv.extract import extract_upload_info
from eserv.monitor import EmailProcessor
from eserv.monitor.result import processed_result
from eserv.upload import DocumentUploader, UploadStatus
from eserv.util.config import Config
from eserv.util.email_state import EmailState
from eserv.util.error_tracking import ErrorTracker, PipelineStage
from eserv.util.notifications import Notifier

if TYPE_CHECKING:
    from pathlib import Path

    from eserv.monitor.result import ProcessedResult
    from eserv.monitor.types import BatchResult, EmailRecord
    from eserv.upload import UploadResult


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """Configuration for pipeline execution."""

    config: Config
    state: EmailState
    tracker: ErrorTracker


class Pipeline:
    """Unified document processing pipeline."""

    def __init__(self, env_path: Path | None = None) -> None:
        """Initialize pipeline with configuration."""
        self.config = Config.from_env(env_path)
        self.state = EmailState(self.config.state.state_file)
        self.tracker = ErrorTracker(self.config.paths.service_dir / 'error_log.json')

    def process(self, record: EmailRecord) -> UploadResult:
        """Process HTML file through complete pipeline.

        Args:
            record (EmailRecord):
                The data for the email to be processed.

        Returns:
            UploadResult with status and details.

        """
        cons = console.bind(uid=record.uid)

        config = self.config
        state = self.state

        with self.tracker.track(record.uid) as tracker:
            # Parse email HTML
            try:
                soup = BeautifulSoup(record.html_body, features='html.parser')
            except Exception as e:
                raise tracker.error(
                    message=f'Failed to initialize soup from html: {e!s}',
                    stage=PipelineStage.EMAIL_PARSING,
                ) from e
            else:
                cons.info(event='Parsed email HTML')

            # Download documents
            try:
                doc_name, store_path = download_documents(soup)
            except Exception as e:
                raise tracker.error(
                    message=f'Failed to download documents: {e!s}',
                    stage=PipelineStage.DOCUMENT_DOWNLOAD,
                ) from e
            else:
                cons.info(
                    event='Downloaded documents',
                    doc_name=doc_name,
                    store_path=store_path.as_posix(),
                )

            # Extract metadata
            try:
                upload_info = extract_upload_info(soup, store_path)
                case_name = upload_info.case_name or 'unknown'
            except Exception as e:
                raise tracker.error(
                    message=f'Failed to parse upload information: {e!s}',
                    stage=PipelineStage.EMAIL_PARSING,
                ) from e
            else:
                cons = console.bind(case_name=case_name)
                cons.info(
                    event='Extracted upload info',
                    doc_name=doc_name,
                    doc_count=upload_info.doc_count,
                )

            if record.uid and state.is_processed(record.uid):
                cons.info('Email already processed, skipping')
                return UploadResult(status=UploadStatus.NO_WORK, folder_path='', uploaded_files=[])

            pdfs = [*store_path.glob('*.pdf')]

            # Get Dropbox credentials for token refresh
            dbx_cred = config.credentials['dropboxOAuth2Api']

            result = DocumentUploader(
                cache_path=config.cache.index_file,
                dbx_token=dbx_cred.access_token,
                notifier=Notifier(config.smtp),
                manual_review_folder=config.paths.manual_review_folder,
                dbx_app_key=dbx_cred.client_id,
                dbx_app_secret=dbx_cred.client_secret,
                dbx_refresh_token=dbx_cred.refresh_token,
            ).process_documents(case_name, pdfs, doc_name)

            match result.status:
                case UploadStatus.SUCCESS:
                    cons.info(
                        event='Upload successful',
                        folder=result.folder_path,
                        files=len(result.uploaded_files),
                    )
                case UploadStatus.MANUAL_REVIEW:
                    tracker.warning(
                        message='No folder match found, sent to manual review',
                        stage=PipelineStage.FOLDER_MATCHING,
                        context={'folder': result.folder_path},
                    )
                case UploadStatus.NO_WORK:
                    tracker.warning(
                        message='No PDF files found after download',
                        stage=PipelineStage.DOCUMENT_DOWNLOAD,
                    )
                case UploadStatus.ERROR:
                    raise tracker.error(
                        message=result.error_msg,
                        stage=PipelineStage.DROPBOX_UPLOAD,
                    )

            return result

    def monitor(self, num_days: int = 1) -> BatchResult:
        """Monitor email inbox and process new messages.

        Args:
            num_days: Process emails from past N days.

        Returns:
            BatchResult with summary and per-email results.

        """
        return EmailProcessor(self).process_batch(num_days)

    def execute(self, rec: EmailRecord) -> ProcessedResult:
        """Execute pipeline for a single email record.

        Args:
            rec (EmailRecord):
                The email record to process.

        Returns:
            ProcessedResult with processing status and error information if applicable.

        """
        try:
            self.process(rec)
        except PipelineError as e:
            return processed_result(rec, error=e.info())
        except Exception as e:
            return processed_result(rec, error={'category': 'unknown', 'message': str(e)})
        else:
            return processed_result(rec, error=None)
