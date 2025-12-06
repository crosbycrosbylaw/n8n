__all__ = ['PipelineStage', 'UploadStatus']
from enum import Enum


class PipelineStage(Enum):
    """Pipeline stages for error categorization."""

    UNKNOWN = 'unknown'
    EMAIL_PARSING = 'parsing'
    DOCUMENT_DOWNLOAD = 'download'
    PDF_EXTRACTION = 'extraction'
    FOLDER_MATCHING = 'matching'
    DROPBOX_UPLOAD = 'upload'


class UploadStatus(Enum):
    """Upload result status."""

    SUCCESS = 'success'
    NO_WORK = 'no_work'
    MANUAL_REVIEW = 'manual_review'
    ERROR = 'error'
