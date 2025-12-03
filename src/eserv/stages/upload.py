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

from functools import partial

__all__ = ['upload_documents']

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from dropbox.exceptions import ApiError
from dropbox.files import FolderMetadata, WriteMode
from rampy import console

from eserv.stages import status
from eserv.stages.types import UploadResult
from eserv.util import stage
from eserv.util.index_cache import IndexCache
from eserv.util.notifications import Notifier
from eserv.util.target_finder import FolderMatcher

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from dropbox import Dropbox
    from dropbox.files import Metadata

    from eserv.types import Config, OAuthCredential

    type ResultEntries = Iterable[Metadata]
    type ResultCursor = str


@dataclass(slots=True)
class DropboxManager:
    """Dropbox client wrapper from an OAuth credential.

    Attributes:
        credential: OAuth credential containing access token.

    """

    credential: OAuthCredential
    uploaded: list[str] = field(init=False, default_factory=list)
    _client: Dropbox | None = field(init=False, default=None, repr=False)

    def index(self) -> dict[str, Any]:
        """Return the Dropbox folder index as a dictionary."""
        dropbox = self.client

        out: dict[str, Any] = {}

        cons = console.bind()
        cons.info('Refreshing Dropbox index from API')

        if result := dropbox.files_list_folder('/Clio/', recursive=True):
            metadata_entries = cast('Iterable[Metadata]', result.entries)

            while True:
                for entry in metadata_entries:
                    if isinstance(entry, FolderMetadata):
                        out[entry.path_display] = {'name': entry.name, 'id': entry.id}

                if not result.has_more:
                    break

                cursor = cast('str', result.cursor)
                result = dropbox.files_list_folder_continue(cursor)

        return out

    def upload(self, path: Path, dropbox_path: str) -> None:
        cons = console.bind(path=path.as_posix(), dropbox_path=dropbox_path)

        with path.open('rb') as f:
            self.client.files_upload(f.read(), dropbox_path, mode=WriteMode.overwrite)

        cons.info('Uploaded file to Dropbox')

        self.uploaded.append(dropbox_path)

    @property
    def client(self) -> Dropbox:
        """Lazily create Dropbox client from credential.

        Returns:
            Dropbox client instance.

        """
        if self._client is None:
            from dropbox import Dropbox

            self._client = Dropbox(
                oauth2_access_token=self.credential.access_token,
                oauth2_refresh_token=self.credential.refresh_token,
                app_key=self.credential.client_id,
                app_secret=self.credential.client_secret,
            )
        return self._client


def upload_documents(
    documents: Sequence[Path],
    case_name: str | None = None,
    lead_name: str | None = None,
    *,
    config: Config,
    min_score: int = 70,
) -> UploadResult:
    """Process and upload document(s) to Dropbox.

    Args:
        documents (Sequence[Path]): A sequence of local PDF file paths to upload.
        case_name (str | None): The case name extracted from the email, if it exists.
        lead_name (str | None):  The filename for the lead document in the set, if it exists.
        config (Config): The pipeline configuration. Used to initialize the uploader.
        min_score (int): The minimum score of a match for it to be used as the target.

    Returns:
        Upload result with status and details.

    """
    cons = console.bind()

    if not documents:
        cons.warning('There are no documents to upload.')
        return UploadResult(status=status.NO_WORK)

    dbx = DropboxManager(config.credentials['dropbox'])
    cache = IndexCache(config.cache.index_file, ttl_hours=4)

    if cache.is_stale():
        try:
            cache.refresh(index := dbx.index())
            cons.info('Dropbox index refreshed', folder_count=len(index))
        except ApiError as e:
            return UploadResult(status.ERROR, error=f'Failed to refresh Dropbox index: {e!s}')

    notifier = Notifier(config.smtp)

    if (
        match := (case_name := case_name or 'Unknown') != 'Unknown'
        and (matcher := FolderMatcher(cache.get_all_paths(), min_score))
        and matcher.find_best_match(case_name)
    ):
        target_folder = match.folder_path
        upload_status = status.SUCCESS
    else:
        target_folder = config.paths.manual_review_folder
        upload_status = status.MANUAL_REVIEW

    partial_result = partial[UploadResult](
        UploadResult,
        status=upload_status,
        folder_path=target_folder,
        uploaded_files=dbx.uploaded,
    )

    try:
        for i, path in enumerate(documents):
            # Determine filename
            if lead_name is None:
                filename = path.name or f'document_{i + 1}.pdf'
            else:
                suffix = '.pdf' if not len(documents) <= 1 else f'_{i + 1}.pdf'
                filename = f'{lead_name.removesuffix(".pdf")}{suffix}'

            dbx.upload(path, f'{target_folder}/{filename}')

        if upload_status == status.SUCCESS:
            notifier.notify_upload_success(case_name, target_folder, len(dbx.uploaded))
        else:
            context = {'uploaded_to': target_folder}
            notifier.notify_manual_review(case_name, 'No matching folder found', context)

        partial_result.keywords.update(match=match or None)

    except Exception as e:
        partial_result.keywords.update(status=status.ERROR, error=str(e))
        notifier.notify_error(case_name, stage.DROPBOX_UPLOAD.value, str(e))

    return partial_result()
