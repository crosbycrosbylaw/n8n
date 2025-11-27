"""A file handling automation pipeline for internal use."""

__all__ = [
    'Config',
    'DocumentUploader',
    'EmailState',
    'ErrorTracker',
    'PipelineStage',
    'UploadResult',
    'UploadStatus',
    'download_documents',
    'extract_aspnet_form_data',
    'extract_download_info',
    'extract_filename_from_disposition',
    'extract_links_from_response_html',
    'extract_post_request_url',
    'extract_upload_info',
    'get_document_store',
    'main',
]

from .download import download_documents
from .extract import (
    extract_aspnet_form_data,
    extract_download_info,
    extract_filename_from_disposition,
    extract_links_from_response_html,
    extract_post_request_url,
    extract_upload_info,
)
from .main import main
from .upload import DocumentUploader, UploadResult, UploadStatus
from .util import Config, EmailState, ErrorTracker, PipelineStage
from .util.doc_store import get_document_store
