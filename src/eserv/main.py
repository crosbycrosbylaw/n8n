"""Main orchestration for document processing pipeline.

Coordinates the full workflow:
1. Parse email HTML
2. Download documents
3. Extract metadata
4. Upload to Dropbox with folder matching
5. Track state and errors
"""

from __future__ import annotations

import typing

from bs4 import BeautifulSoup

from .download import download_documents
from .extract import extract_upload_info
from .upload import DocumentUploader, UploadStatus
from .util import Config, EmailState, ErrorTracker, Notifier, PipelineStage, hash_email_subject

if typing.TYPE_CHECKING:
    from pathlib import Path

from rampy import console


def main(path: Path) -> None:
    """Process an email HTML file through the complete pipeline.

    Args:
        path: Path to email HTML file.

    """
    cons = console.bind()
    config = Config.from_env()

    # Initialize state tracking
    email_state = EmailState(config.email_state.state_file)
    error_tracker = ErrorTracker(config.paths.service_dir / 'error_log.json')

    # Parse email HTML
    try:
        with path.resolve(strict=True).open() as io:
            soup = BeautifulSoup(io, 'html.parser')

        cons.info('Parsed email HTML', email_path=path.as_posix())

    except Exception as e:
        cons.exception('Failed to parse email HTML', email_path=path.as_posix())

        error_tracker.log_error(
            email_hash='unknown',
            stage=PipelineStage.EMAIL_PARSING,
            error_message=str(e),
        )

        return

    # Download documents

    try:
        doc_name, store_path = download_documents(soup)

    except Exception as e:
        cons.exception('Failed to download documents')

        error_tracker.log_error(
            email_hash='unknown',
            stage=PipelineStage.DOCUMENT_DOWNLOAD,
            error_message=str(e),
        )

        return
    else:
        cons.info('Downloaded documents', doc_name=doc_name, store_path=store_path.as_posix())

    # Extract metadata
    try:
        upload_info = extract_upload_info(soup, store_path)

        doc_count = upload_info.doc_count
        case_name = upload_info.case_name or 'unknown'

    except Exception as e:
        cons.exception('Failed to extract upload info')

        error_tracker.log_error(
            email_hash='unknown',
            stage=PipelineStage.EMAIL_PARSING,
            error_message=str(e),
        )

        return

    else:
        cons = console.bind(case_name=case_name)
        cons.info('Extracted upload info', doc_name=doc_name, doc_count=doc_count)

    # Check if already processed
    if case_name and email_state.is_processed(case_name):
        cons.info('Email already processed, skipping')
        return

    # Get list of PDF files to upload

    if not (pdf_files := [*store_path.glob('*.pdf')]):
        cons.warning('No PDF files found in store', store_path=store_path.as_posix())

        error_tracker.log_error(
            email_hash=hash_email_subject(case_name),
            stage=PipelineStage.DOCUMENT_DOWNLOAD,
            error_message='No PDF files found after download',
        )

        return

    # Initialize uploader

    notifier = Notifier(config.smtp)

    uploader = DocumentUploader(
        cache_path=config.cache.index_file,
        dbx_token=config.dropbox.token,
        notifier=notifier,
        manual_review_folder=config.paths.manual_review_folder,
    )

    result = uploader.process_document(case_name, pdf_files, doc_name)
    email_hash = hash_email_subject(case_name)

    if result.status == UploadStatus.SUCCESS:
        email_state.mark_processed(subject=case_name, matched_folder=result.folder_path)

        cons.info('Upload successful', folder=result.folder_path, files=len(result.uploaded_files))

    elif result.status == UploadStatus.MANUAL_REVIEW:
        email_state.mark_processed(subject=case_name, matched_folder=None)

        error_tracker.log_error(
            email_hash=email_hash,
            stage=PipelineStage.FOLDER_MATCHING,
            error_message='No folder match found, sent to manual review',
            context={'folder': result.folder_path},
        )

        cons.warning('Upload sent to manual review', folder=result.folder_path)

    elif result.status == UploadStatus.ERROR:
        error_tracker.log_error(
            email_hash=email_hash,
            stage=PipelineStage.DROPBOX_UPLOAD,
            error_message=result.error_msg,
        )

        cons.error('Upload failed', reason=result.error_msg)
