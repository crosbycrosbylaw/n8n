# ruff: noqa: BLE001
from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from rampy.util import create_field_factory

from eserv import (
    config_factory,
    download_documents,
    error_tracker_factory,
    extract_upload_info,
    result_factory,
    state_tracker_factory,
    upload_documents,
)
from eserv.enums import stage, status
from eserv.errors import *
from eserv.types import EmailProcessor, UploadResult
from setup_console import console

if TYPE_CHECKING:
    from pathlib import Path

    from eserv.types import BatchResult, EmailRecord, ProcessedResult


def _parse_html(content: str) -> BeautifulSoup:
    try:
        soup = BeautifulSoup(content, features='html.parser')
    except (TypeError, UnicodeDecodeError) as e:
        raise EmailParseError from e
    else:
        return soup


class Pipeline:
    """Unified document processing pipeline."""

    def __init__(self, dotenv_path: Path | None = None) -> None:
        """Initialize pipeline with configuration."""
        self.config = config_factory(dotenv_path)
        self.state = state_tracker_factory(self.config.state.state_file)
        self.tracker = error_tracker_factory(self.config.paths.service_dir / 'error_log.json')

    def process(self, record: EmailRecord) -> UploadResult:
        """Process HTML file through complete pipeline.

        Args:
            record (EmailRecord):
                The data for the email to be processed.

        Returns:
            UploadResult with status and details.

        """
        subcons = console.bind(uid=record.uid)

        with self.tracker.track(record.uid) as tracker:
            # Parse email HTML
            try:
                soup = _parse_html(record.html_body)
            except EmailParseError as e:
                return tracker.error(
                    event='BeautifulSoup initialization',
                    exception=e,
                    context={'html_body_length': len(record.html_body)},
                )
            except Exception as e:
                wrapped = EmailParseError()
                return tracker.error(
                    event='BeautifulSoup initialization',
                    exception=wrapped,
                    context={'html_body_length': len(record.html_body), 'original_error': str(e)},
                )
            else:
                subcons.info(event='Parsed HTML body')

            # Download documents
            try:
                doc_name, store_path = download_documents(soup)
            except DocumentDownloadError as e:
                return tracker.error(exception=e)
            except Exception as e:
                wrapped = DocumentDownloadError()
                return tracker.error(exception=wrapped, context={'original_error': str(e)})
            else:
                subcons.info(
                    event='Downloaded documents',
                    doc_name=doc_name,
                    store_path=store_path.as_posix(),
                )

            # Extract metadata
            try:
                upload_info = extract_upload_info(soup, store_path)
                case_name = upload_info.case_name or 'unknown'
            except EmailParseError as e:
                return tracker.error(
                    event='UploadInfo extraction',
                    exception=e,
                    context={'store_path': store_path.as_posix()},
                )
            except Exception as e:
                wrapped = EmailParseError()
                return tracker.error(
                    event='UploadInfo extraction',
                    exception=wrapped,
                    context={'store_path': store_path.as_posix(), 'original_error': str(e)},
                )
            else:
                subcons = console.bind(case_name=case_name)
                subcons.info(
                    event='Extracted upload info',
                    doc_name=doc_name,
                    doc_count=upload_info.doc_count,
                )

            if record.uid and self.state.is_processed(record.uid):
                subcons.info('Email already processed, skipping')
                return UploadResult(status=status.NO_WORK)

            pdfs = [*store_path.glob('*.pdf')]
            result = upload_documents(pdfs, case_name, doc_name, config=self.config)

            match result.status:
                case status.SUCCESS:
                    subcons.info(
                        event='Upload successful',
                        folder=result.folder_path,
                        files=len(result.uploaded_files),
                    )
                case status.MANUAL_REVIEW:
                    tracker.warning(
                        message='No folder match found, sent to manual review',
                        stage=stage.FOLDER_MATCHING,
                        context={'folder': result.folder_path},
                    )
                case status.NO_WORK:
                    tracker.warning(
                        message='No PDF files found after download',
                        stage=stage.DOCUMENT_DOWNLOAD,
                        context={'store_path': store_path.as_posix()},
                    )
                case status.ERROR:
                    tracker.error(
                        exception=(
                            exc := PipelineError.from_stage(
                                stage.DROPBOX_UPLOAD,
                                message=result.error_msg,
                            )
                        ),
                        folder_path=result.folder_path,
                        uploaded_files=result.uploaded_files,
                        case_name=case_name,
                    )

                    raise exc

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
            result = self.process(rec)
        except PipelineError as e:
            return result_factory(record=rec, error=e.entry())
        except Exception as e:
            console.exception('Something went wrong.', uid=rec.uid)

            from_exc = PipelineError(message=type(e).__name__, args=e.args)
            return result_factory(record=rec, error=from_exc.entry())
        else:
            # Check if process() returned an error result
            if result.status == status.ERROR:
                # Get the error details from the tracker
                error_entry = self.tracker.prev_error
                return result_factory(record=rec, error=error_entry)
            return result_factory(record=rec, error=None)


pipeline_factory = create_field_factory(Pipeline)
