from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from rampy import console

from eserv import (
    config,
    download_documents,
    extract_upload_info,
    processed_result,
    status,
    upload_documents,
)
from eserv.errors import PipelineError
from eserv.monitor.processor import EmailProcessor
from eserv.types import EmailState, ErrorTracker, PipelineStage, UploadResult

if TYPE_CHECKING:
    from pathlib import Path

    from eserv.monitor.types import BatchResult, EmailRecord, ProcessedResult
    from eserv.util.configuration import Config


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
        self.config = config(env_path)
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

        with self.tracker.track(record.uid) as tracker:
            # Parse email HTML
            try:
                soup = BeautifulSoup(record.html_body, features='html.parser')
            except Exception as e:
                tracker.error(
                    message=f'Failed to initialize soup from html: {e!s}',
                    stage=PipelineStage.EMAIL_PARSING,
                    context={
                        'exception_type': type(e).__name__,
                        'traceback': traceback.format_exc(),
                        'html_body_length': len(record.html_body),
                    },
                    raises=True,
                )
            else:
                cons.info(event='Parsed email HTML')

            # Download documents
            try:
                doc_name, store_path = download_documents(soup)
            except Exception as e:
                tracker.error(
                    message=f'Failed to download documents: {e!s}',
                    stage=PipelineStage.DOCUMENT_DOWNLOAD,
                    context={
                        'exception_type': type(e).__name__,
                        'traceback': traceback.format_exc(),
                    },
                    raises=True,
                )
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
                tracker.error(
                    message=f'Failed to parse upload information: {e!s}',
                    stage=PipelineStage.EMAIL_PARSING,
                    context={
                        'exception_type': type(e).__name__,
                        'traceback': traceback.format_exc(),
                        'store_path': store_path.as_posix(),
                    },
                    raises=True,
                )
            else:
                cons = console.bind(case_name=case_name)
                cons.info(
                    event='Extracted upload info',
                    doc_name=doc_name,
                    doc_count=upload_info.doc_count,
                )

            if record.uid and self.state.is_processed(record.uid):
                cons.info('Email already processed, skipping')
                return UploadResult(status=status.NO_WORK)

            pdfs = [*store_path.glob('*.pdf')]

            result = upload_documents(case_name, pdfs, doc_name, config=self.config)

            match result.status:
                case status.SUCCESS:
                    cons.info(
                        event='Upload successful',
                        folder=result.folder_path,
                        files=len(result.uploaded_files),
                    )
                case status.MANUAL_REVIEW:
                    tracker.warning(
                        message='No folder match found, sent to manual review',
                        stage=PipelineStage.FOLDER_MATCHING,
                        context={'folder': result.folder_path},
                    )
                case status.NO_WORK:
                    tracker.warning(
                        message='No PDF files found after download',
                        stage=PipelineStage.DOCUMENT_DOWNLOAD,
                        context={'store_path': store_path.as_posix()},
                    )
                case status.ERROR:
                    tracker.error(
                        message=result.error_msg,
                        stage=PipelineStage.DROPBOX_UPLOAD,
                        context={
                            'folder_path': result.folder_path,
                            'uploaded_files': result.uploaded_files,
                            'case_name': case_name,
                        },
                        raises=True,
                    )

            return result

    def monitor(self, num_days: int = 1) -> BatchResult:
        """Monitor email inbox and process new messages.

        Args:
            num_days: Process emails from past N days.

        Returns:
            BatchResult with summary and per-email results.

        """
        # Clean up old error logs (keep last 30 days)
        self.tracker.clear_old_errors(days=30)

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
