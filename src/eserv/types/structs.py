__all__ = ['DownloadInfo', 'EmailInfo', 'EmailRecord', 'PartialEmailRecord', 'UploadInfo']

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class PartialEmailRecord:
    """Basic email metadata fetched from Outlook."""

    uid: str
    sender: str
    subject: str


EmailInfo = PartialEmailRecord


@dataclass(frozen=True, slots=True)
class EmailRecord(EmailInfo):
    """All relevant email metadata fetched from Outlook."""

    received_at: datetime
    html_body: str


@dataclass(slots=True, frozen=True)
class UploadInfo:
    """Information about an upload operation.

    Attributes:
        doc_count: The number of documents uploaded.
        case_name: The name of the case associated with the upload, or None if not applicable.

    """

    doc_count: int
    case_name: str | None


@dataclass(slots=True, frozen=True)
class DownloadInfo:
    """Information about a file to be downloaded.

    Attributes:
        source (str): The URL or path from which to download the file.
        filename (str): The name to use when saving the downloaded file.

    """

    source: str
    doc_name: str | None
