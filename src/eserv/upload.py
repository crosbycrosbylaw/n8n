"""Document upload orchestration with Dropbox integration.

Handles the complete upload workflow:
1. Load/refresh Dropbox folder index
2. Match case name to folder using fuzzy matching
3. Upload document(s) to matched folder or manual review folder
4. Track state and errors

Classes:
    DocumentUploader: Main upload orchestration class.
"""

# pyright: reportUnknownMemberType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportMissingTypeStubs=false

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, NoReturn, cast

import requests
from dropbox import Dropbox
from dropbox.exceptions import ApiError
from dropbox.files import FolderMetadata, WriteMode
from rampy import console

from .util import FolderMatcher, IndexCache, PipelineStage

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from dropbox.files import Metadata

    from .util import CaseMatch, Notifier

    type ResultEntries = Iterable[Metadata]
    type ResultCursor = str


class UploadStatus(Enum):
    """Upload result status."""

    SUCCESS = 'success'
    MANUAL_REVIEW = 'manual_review'
    ERROR = 'error'


@dataclass(slots=True, frozen=True)
class UploadResult:
    """Result of a document upload operation.

    Attributes:
        status: Upload status (success, manual_review, or error).
        folder_path: Dropbox folder path (or manual review folder).
        uploaded_files: List of uploaded file paths.
        match: Case match details if applicable.
        error: Error message if status is ERROR.

    """

    status: UploadStatus
    folder_path: str
    uploaded_files: list[str]
    match: CaseMatch | None = None
    error: str | None = None

    @property
    def error_msg(self) -> str:
        """Get the error message.

        Returns:
            The error message, or 'unknown upload error' if no error is set.

        """
        return self.error or 'unknown upload error'


def _raise_missing_token() -> NoReturn:
    message = 'No access token in refresh response'
    raise ValueError(message)


@dataclass
class DocumentUploader:
    """Orchestrates document upload workflow with Dropbox.

    Attributes:
        cache_path: Path to Dropbox index cache file.
        dbx_token: Dropbox API token.
        notifier: Email notifier for alerts.
        manual_review_folder: Dropbox folder for manual review uploads.
        min_match_score: Minimum confidence score for folder matching.
        dbx_app_key: Dropbox app key (for auto-refresh).
        dbx_app_secret: Dropbox app secret (for auto-refresh).
        dbx_refresh_token: Dropbox refresh token (for auto-refresh).

    """

    cache_path: Path
    dbx_token: str
    notifier: Notifier
    manual_review_folder: str
    min_match_score: float = 70.0
    dbx_app_key: str | None = None
    dbx_app_secret: str | None = None
    dbx_refresh_token: str | None = None

    def __post_init__(self) -> None:
        """Initialize Dropbox client and index cache."""
        self.dbx = Dropbox(self.dbx_token)

        self.cache = IndexCache(self.cache_path, ttl_hours=4)

    def _refresh_access_token(self) -> str:
        """Refresh Dropbox access token using refresh token.

        Returns:
            New access token.

        Raises:
            ValueError: If refresh token credentials are not configured.

        """
        cons = console.bind()

        if not all([self.dbx_app_key, self.dbx_app_secret, self.dbx_refresh_token]):
            message = 'Dropbox refresh token credentials not configured'
            raise ValueError(message)

        cons.info('Refreshing Dropbox access token')

        try:
            response = requests.post(
                url='https://api.dropboxapi.com/oauth2/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.dbx_refresh_token,
                    'client_id': self.dbx_app_key,
                    'client_secret': self.dbx_app_secret,
                },
                timeout=120,
            )
            response.raise_for_status()
            tokens = response.json()

            new_token = tokens.get('access_token')

            if not new_token:
                _raise_missing_token()

            # Update Dropbox client with new token
            self.dbx = Dropbox(new_token)
            self.dbx_token = new_token

            cons.info('Dropbox access token refreshed successfully')

        except Exception:
            cons.exception('Failed to refresh Dropbox access token')
            raise
        else:
            return new_token

    def _refresh_index_if_needed(self) -> None:
        """Refresh Dropbox folder index if cache is stale."""
        cons = console.bind()

        if not self.cache.is_stale():
            cons.info('Using cached Dropbox index')

            return None

        cons.info('Refreshing Dropbox index from API')

        try:
            # List all folders in Dropbox
            folders: dict[str, Any] = {}

            result = self.dbx.files_list_folder('/Clio/', recursive=True)

            while True:
                for entry in cast('Iterable[Metadata]', result.entries):
                    if isinstance(entry, FolderMetadata):
                        folders[entry.path_display] = {'name': entry.name, 'id': entry.id}

                if not result.has_more:
                    break

                result = self.dbx.files_list_folder_continue(cast('str', result.cursor))

            self.cache.refresh(folders)

            cons.info('Dropbox index refreshed', folder_count=len(folders))

        except ApiError as e:
            # Check if token expired
            if 'expired_access_token' in str(e).lower():
                cons.warning('Access token expired, attempting refresh')

                if all([self.dbx_app_key, self.dbx_app_secret, self.dbx_refresh_token]):
                    try:
                        self._refresh_access_token()
                        return self._refresh_index_if_needed()
                    except:
                        cons.exception('Token refresh failed, cannot continue')
                        raise

            cons.exception('Failed to refresh Dropbox index')
            raise

    def _upload_file_to_dropbox(self, local_path: Path, dropbox_path: str) -> None:
        """Upload a single file to Dropbox.

        Args:
            local_path: Local file path.
            dropbox_path: Target Dropbox path (including filename).

        """
        cons = console.bind(local_path=local_path.as_posix(), dropbox_path=dropbox_path)

        with local_path.open('rb') as f:
            self.dbx.files_upload(f.read(), dropbox_path, mode=WriteMode.overwrite)

        cons.info('Uploaded file to Dropbox')

    def process_document(
        self,
        case_name: str | None,
        documents: Sequence[Path],
        lead_doc_name: str | None = None,
    ) -> UploadResult:
        """Process and upload document(s) to Dropbox.

        Args:
            case_name: Case name extracted from email.
            documents: List of local PDF file paths to upload.
            lead_doc_name: Base filename for uploads (uses doc name or generates).

        Returns:
            Upload result with status and details.

        """
        cons = console.bind(case_name=f'{case_name}')

        # Refresh index if needed
        try:
            self._refresh_index_if_needed()
        except Exception as e:
            return UploadResult(
                status=UploadStatus.ERROR,
                folder_path='',
                uploaded_files=[],
                error=f'Failed to refresh Dropbox index: {e}',
            )

        # Get folder paths for matching
        folder_paths = self.cache.get_all_paths()

        # Try to match case name to folder
        match = None
        if case_name:
            matcher = FolderMatcher(folder_paths, min_score=self.min_match_score)
            match = matcher.find_best_match(case_name)

        # Determine target folder
        if match:
            target_folder = match.folder_path
            status = UploadStatus.SUCCESS
        else:
            target_folder = self.manual_review_folder
            status = UploadStatus.MANUAL_REVIEW

            cons.warning('No folder match found, uploading to manual review')

        # Upload files
        uploaded: list[str] = []

        try:
            for i, local_path in enumerate(documents):
                # Determine filename
                if lead_doc_name:
                    if len(documents) > 1:
                        # Multiple files: add enumeration suffix
                        filename = f'{lead_doc_name}_{i + 1}.pdf'
                    else:
                        filename = f'{lead_doc_name}.pdf'
                else:
                    # No base filename: use original name or generate
                    filename = local_path.name or f'document_{i + 1}.pdf'

                dropbox_path = f'{target_folder}/{filename}'
                self._upload_file_to_dropbox(local_path, dropbox_path)
                uploaded.append(dropbox_path)

            # Send success notification
            if status == UploadStatus.SUCCESS:
                self.notifier.notify_upload_success(
                    case_name=case_name or 'Unknown',
                    folder_path=target_folder,
                    file_count=len(uploaded),
                )
            else:
                self.notifier.notify_manual_review(
                    case_name=case_name or 'Unknown',
                    reason='No matching folder found',
                    details={'uploaded_to': target_folder},
                )

            return UploadResult(
                status=status,
                folder_path=target_folder,
                uploaded_files=uploaded,
                match=match,
            )

        except Exception as e:
            cons.exception('Upload failed')

            self.notifier.notify_error(
                case_name=case_name or 'Unknown',
                stage=PipelineStage.DROPBOX_UPLOAD.value,
                error=str(e),
            )

            return UploadResult(
                status=UploadStatus.ERROR,
                folder_path=target_folder,
                uploaded_files=uploaded,
                error=str(e),
            )
