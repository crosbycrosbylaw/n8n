"""Unit tests for upload module.

Tests cover:
- DropboxManager lazy client initialization
- Folder index fetching with pagination
- File upload orchestration
- upload_documents workflow
- Folder matching vs manual review routing
- Multi-file naming logic
- Notification dispatch
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from eserv.stages import status
from eserv.stages.upload import DropboxManager, upload_documents

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_credential() -> Mock:
    """Create mock OAuthCredential."""
    cred = Mock()
    cred.access_token = 'test_access_token'
    cred.refresh_token = 'test_refresh_token'
    cred.client_id = 'test_client_id'
    cred.client_secret = 'test_client_secret'
    return cred


@pytest.fixture
def mock_config() -> Mock:
    """Create mock Config object."""
    config = Mock()
    config.credentials = {
        'dropbox': Mock(
            access_token='test_token',
            refresh_token='test_refresh',
            client_id='test_id',
            client_secret='test_secret',
        ),
    }
    config.paths = Mock(manual_review_folder='/Clio/Manual Review/')
    config.cache = Mock(index_file=Path('/tmp/index_cache.json'), ttl_hours=4)
    config.smtp = Mock(
        server='smtp.test.com',
        port=587,
        from_addr='test@example.com',
        to_addr='recipient@example.com',
    )
    return config


@pytest.fixture
def mock_pdf_file(tempdir: Path) -> Path:
    """Create mock PDF file."""
    pdf_path = tempdir / 'test_document.pdf'
    pdf_path.write_bytes(b'%PDF-1.4\nMock PDF content')
    return pdf_path


class TestDropboxManagerClient:
    """Test DropboxManager lazy client initialization."""

    def test_lazy_client_initialization_on_first_access(self, mock_credential: Mock) -> None:
        """Test client is created lazily on first access."""
        manager = DropboxManager(credential=mock_credential)

        # Verify client not created yet
        assert manager._client is None

        with patch('dropbox.Dropbox') as mock_dropbox_class:
            mock_client = Mock()
            mock_dropbox_class.return_value = mock_client

            # Access client property
            client = manager.client

            # Verify Dropbox SDK constructor called with credentials
            mock_dropbox_class.assert_called_once_with(
                oauth2_access_token='test_access_token',
                oauth2_refresh_token='test_refresh_token',
                app_key='test_client_id',
                app_secret='test_client_secret',
            )

            # Verify client returned
            assert client is mock_client

    def test_client_caching(self, mock_credential: Mock) -> None:
        """Test client is cached after first creation."""
        manager = DropboxManager(credential=mock_credential)

        with patch('dropbox.Dropbox') as mock_dropbox_class:
            mock_client = Mock()
            mock_dropbox_class.return_value = mock_client

            # Access client twice
            client1 = manager.client
            client2 = manager.client

            # Verify Dropbox SDK constructor called only once
            assert mock_dropbox_class.call_count == 1

            # Verify same client returned
            assert client1 is client2


class TestDropboxManagerIndex:
    """Test folder index fetching."""

    def test_successful_folder_index_fetch(self, mock_credential: Mock) -> None:
        """Test successful folder index fetch without pagination."""
        manager = DropboxManager(credential=mock_credential)

        # Mock Dropbox client and files_list_folder response
        mock_client = Mock()
        mock_result = Mock()
        mock_result.has_more = False

        # Create mock entries with proper attributes (avoid Mock's special 'name' attribute)
        from dropbox.files import FolderMetadata

        entry1 = Mock(spec=FolderMetadata)
        entry1.path_display = '/Clio/Smith v. Jones'
        entry1.name = 'Smith v. Jones'
        entry1.id = 'folder_id_1'

        entry2 = Mock(spec=FolderMetadata)
        entry2.path_display = '/Clio/Doe v. Roe'
        entry2.name = 'Doe v. Roe'
        entry2.id = 'folder_id_2'

        mock_result.entries = [entry1, entry2]

        mock_client.files_list_folder.return_value = mock_result

        # Set _client directly since client is a read-only property
        manager._client = mock_client

        # Fetch index
        index = manager.index()

        # Verify files_list_folder called
        mock_client.files_list_folder.assert_called_once_with('/Clio/', recursive=True)

        # Verify index structure
        assert '/Clio/Smith v. Jones' in index
        assert index['/Clio/Smith v. Jones']['name'] == 'Smith v. Jones'
        assert index['/Clio/Smith v. Jones']['id'] == 'folder_id_1'
        assert '/Clio/Doe v. Roe' in index

    def test_pagination_handling(self, mock_credential: Mock) -> None:
        """Test pagination with has_more=True."""
        manager = DropboxManager(credential=mock_credential)

        # Create mock entries with proper attributes
        from dropbox.files import FolderMetadata

        entry1 = Mock(spec=FolderMetadata)
        entry1.path_display = '/Clio/Case1'
        entry1.name = 'Case1'
        entry1.id = 'id1'

        entry2 = Mock(spec=FolderMetadata)
        entry2.path_display = '/Clio/Case2'
        entry2.name = 'Case2'
        entry2.id = 'id2'

        # Mock first page
        mock_result_page1 = Mock()
        mock_result_page1.has_more = True
        mock_result_page1.cursor = 'cursor_123'
        mock_result_page1.entries = [entry1]

        # Mock second page
        mock_result_page2 = Mock()
        mock_result_page2.has_more = False
        mock_result_page2.entries = [entry2]

        mock_client = Mock()
        mock_client.files_list_folder.return_value = mock_result_page1
        mock_client.files_list_folder_continue.return_value = mock_result_page2

        # Set _client directly since client is a read-only property
        manager._client = mock_client

        # Fetch index
        index = manager.index()

        # Verify pagination calls
        mock_client.files_list_folder.assert_called_once()
        mock_client.files_list_folder_continue.assert_called_once_with('cursor_123')

        # Verify both pages in index
        assert '/Clio/Case1' in index
        assert '/Clio/Case2' in index


class TestDropboxManagerUpload:
    """Test file upload functionality."""

    def test_successful_file_upload(
        self,
        mock_credential: Mock,
        mock_pdf_file: Path,
    ) -> None:
        """Test successful file upload to Dropbox."""
        manager = DropboxManager(credential=mock_credential)

        # Mock Dropbox client
        mock_client = Mock()
        mock_metadata = Mock(path_display='/Clio/Smith v. Jones/Motion.pdf')
        mock_client.files_upload.return_value = mock_metadata

        # Set _client directly since client is a read-only property
        manager._client = mock_client

        # Upload file
        manager.upload(mock_pdf_file, '/Clio/Smith v. Jones/Motion.pdf')

        # Verify files_upload called
        mock_client.files_upload.assert_called_once()
        call_args = mock_client.files_upload.call_args
        assert call_args[0][1] == '/Clio/Smith v. Jones/Motion.pdf'

        # Verify file added to uploaded list
        assert len(manager.uploaded) == 1
        assert manager.uploaded[0] == '/Clio/Smith v. Jones/Motion.pdf'

    def test_uploaded_list_tracking(
        self,
        mock_credential: Mock,
        mock_pdf_file: Path,
    ) -> None:
        """Test uploaded files are tracked in list."""
        manager = DropboxManager(credential=mock_credential)

        mock_client = Mock()
        mock_client.files_upload.return_value = Mock()

        # Set _client directly since client is a read-only property
        manager._client = mock_client

        # Upload multiple files
        manager.upload(mock_pdf_file, '/Clio/Case1/Doc1.pdf')
        manager.upload(mock_pdf_file, '/Clio/Case1/Doc2.pdf')
        manager.upload(mock_pdf_file, '/Clio/Case2/Doc3.pdf')

        # Verify all tracked
        assert len(manager.uploaded) == 3
        assert '/Clio/Case1/Doc1.pdf' in manager.uploaded
        assert '/Clio/Case1/Doc2.pdf' in manager.uploaded
        assert '/Clio/Case2/Doc3.pdf' in manager.uploaded


class TestUploadDocuments:
    """Test upload_documents orchestration."""

    def test_successful_upload_to_matched_folder(
        self,
        mock_config: Mock,
        mock_pdf_file: Path,
    ) -> None:
        """Test successful upload when folder match found."""
        # Mock IndexCache
        mock_cache = Mock()
        mock_cache.is_stale.return_value = False
        mock_cache.get_all_paths.return_value = [
            '/Clio/Smith v. Jones',
            '/Clio/Doe v. Roe',
        ]

        # Mock FolderMatcher
        mock_match = Mock()
        mock_match.folder_path = '/Clio/Smith v. Jones'
        mock_matcher = Mock()
        mock_matcher.find_best_match.return_value = mock_match

        # Mock DropboxManager
        mock_dbx = Mock()
        mock_dbx.uploaded = ['/Clio/Smith v. Jones/Motion.pdf']

        # Mock Notifier
        mock_notifier = Mock()

        with patch('eserv.stages.upload.IndexCache', return_value=mock_cache):
            with patch('eserv.stages.upload.FolderMatcher', return_value=mock_matcher):
                with patch('eserv.stages.upload.DropboxManager', return_value=mock_dbx):
                    with patch('eserv.stages.upload.Notifier', return_value=mock_notifier):
                        # Execute upload
                        result = upload_documents(
                            documents=[mock_pdf_file],
                            case_name='Smith v. Jones',
                            lead_name='Motion',
                            config=mock_config,
                        )

                        # Verify result
                        assert result.status == status.SUCCESS
                        assert result.folder_path == '/Clio/Smith v. Jones'

                        # Verify upload called
                        mock_dbx.upload.assert_called_once()

                        # Verify success notification sent
                        mock_notifier.notify_upload_success.assert_called_once()

    def test_manual_review_routing_no_folder_match(
        self,
        mock_config: Mock,
        mock_pdf_file: Path,
    ) -> None:
        """Test manual review routing when no folder match found."""
        # Mock IndexCache
        mock_cache = Mock()
        mock_cache.is_stale.return_value = False
        mock_cache.get_all_paths.return_value = ['/Clio/Smith v. Jones']

        # Mock FolderMatcher with no match
        mock_matcher = Mock()
        mock_matcher.find_best_match.return_value = None

        # Mock DropboxManager
        mock_dbx = Mock()
        mock_dbx.uploaded = ['/Clio/Manual Review/Motion.pdf']

        # Mock Notifier
        mock_notifier = Mock()

        with patch('eserv.stages.upload.IndexCache', return_value=mock_cache):
            with patch('eserv.stages.upload.FolderMatcher', return_value=mock_matcher):
                with patch('eserv.stages.upload.DropboxManager', return_value=mock_dbx):
                    with patch('eserv.stages.upload.Notifier', return_value=mock_notifier):
                        # Execute upload with unknown case
                        result = upload_documents(
                            documents=[mock_pdf_file],
                            case_name='Unknown Case',
                            lead_name='Motion',
                            config=mock_config,
                        )

                        # Verify result
                        assert result.status == status.MANUAL_REVIEW
                        assert result.folder_path == '/Clio/Manual Review/'

                        # Verify upload to manual review folder
                        mock_dbx.upload.assert_called_once()

                        # Verify manual review notification sent
                        mock_notifier.notify_manual_review.assert_called_once()

    def test_empty_document_list_returns_no_work(self, mock_config: Mock) -> None:
        """Test NO_WORK status when no documents provided."""
        # Execute with empty documents list
        result = upload_documents(documents=[], case_name='Smith v. Jones', config=mock_config)

        # Verify NO_WORK status
        assert result.status == status.NO_WORK

    def test_multi_file_naming_logic(
        self,
        mock_config: Mock,
        tempdir,
    ) -> None:
        """Test multi-file naming with numbering."""
        # Create multiple PDF files
        tmp = tempdir
        pdf1 = tmp / 'doc1.pdf'
        pdf2 = tmp / 'doc2.pdf'
        pdf3 = tmp / 'doc3.pdf'
        pdf1.write_bytes(b'%PDF-1.4\nDoc1')
        pdf2.write_bytes(b'%PDF-1.4\nDoc2')
        pdf3.write_bytes(b'%PDF-1.4\nDoc3')

        # Mock dependencies
        mock_cache = Mock()
        mock_cache.is_stale.return_value = False
        mock_cache.get_all_paths.return_value = ['/Clio/Smith v. Jones']

        mock_match = Mock()
        mock_match.folder_path = '/Clio/Smith v. Jones'
        mock_matcher = Mock()
        mock_matcher.find_best_match.return_value = mock_match

        mock_dbx = Mock()
        mock_dbx.uploaded = []

        mock_notifier = Mock()

        with patch('eserv.stages.upload.IndexCache', return_value=mock_cache):
            with patch('eserv.stages.upload.FolderMatcher', return_value=mock_matcher):
                with patch('eserv.stages.upload.DropboxManager', return_value=mock_dbx):
                    with patch('eserv.stages.upload.Notifier', return_value=mock_notifier):
                        # Execute upload with multiple files
                        upload_documents(
                            documents=[pdf1, pdf2, pdf3],
                            case_name='Smith v. Jones',
                            lead_name='Motion',
                            config=mock_config,
                        )

                        # Verify upload called 3 times with numbered filenames
                        assert mock_dbx.upload.call_count == 3

    def test_cache_refresh_on_stale_index(
        self,
        mock_config: Mock,
        mock_pdf_file: Path,
    ) -> None:
        """Test cache is refreshed when stale."""
        # Mock IndexCache as stale
        mock_cache = Mock()
        mock_cache.is_stale.return_value = True
        mock_cache.get_all_paths.return_value = ['/Clio/Smith v. Jones']

        # Mock DropboxManager.index()
        mock_dbx = Mock()
        mock_dbx.index.return_value = {'/Clio/Smith v. Jones': {'name': 'Smith v. Jones'}}
        mock_dbx.uploaded = []

        # Mock FolderMatcher
        mock_match = Mock()
        mock_match.folder_path = '/Clio/Smith v. Jones'
        mock_matcher = Mock()
        mock_matcher.find_best_match.return_value = mock_match

        mock_notifier = Mock()

        with patch('eserv.stages.upload.IndexCache', return_value=mock_cache):
            with patch('eserv.stages.upload.FolderMatcher', return_value=mock_matcher):
                with patch('eserv.stages.upload.DropboxManager', return_value=mock_dbx):
                    with patch('eserv.stages.upload.Notifier', return_value=mock_notifier):
                        # Execute upload
                        upload_documents(
                            documents=[mock_pdf_file],
                            case_name='Smith v. Jones',
                            config=mock_config,
                        )

                        # Verify index refreshed
                        mock_dbx.index.assert_called_once()
                        mock_cache.refresh.assert_called_once()

    def test_notification_sent_for_each_outcome(
        self,
        mock_config: Mock,
        mock_pdf_file: Path,
    ) -> None:
        """Test notifications are sent for success and manual review."""
        mock_cache = Mock()
        mock_cache.is_stale.return_value = False
        mock_cache.get_all_paths.return_value = ['/Clio/Smith v. Jones']

        mock_dbx = Mock()
        mock_dbx.uploaded = []

        mock_notifier = Mock()

        # Test success notification
        mock_match = Mock()
        mock_match.folder_path = '/Clio/Smith v. Jones'
        mock_matcher = Mock()
        mock_matcher.find_best_match.return_value = mock_match

        with patch('eserv.stages.upload.IndexCache', return_value=mock_cache):
            with patch('eserv.stages.upload.FolderMatcher', return_value=mock_matcher):
                with patch('eserv.stages.upload.DropboxManager', return_value=mock_dbx):
                    with patch('eserv.stages.upload.Notifier', return_value=mock_notifier):
                        upload_documents(
                            documents=[mock_pdf_file],
                            case_name='Smith v. Jones',
                            config=mock_config,
                        )

                        # Verify success notification
                        mock_notifier.notify_upload_success.assert_called_once()

        # Test manual review notification
        mock_matcher.find_best_match.return_value = None
        mock_notifier.reset_mock()

        with patch('eserv.stages.upload.IndexCache', return_value=mock_cache):
            with patch('eserv.stages.upload.FolderMatcher', return_value=mock_matcher):
                with patch('eserv.stages.upload.DropboxManager', return_value=mock_dbx):
                    with patch('eserv.stages.upload.Notifier', return_value=mock_notifier):
                        upload_documents(
                            documents=[mock_pdf_file],
                            case_name='Unknown Case',
                            config=mock_config,
                        )

                        # Verify manual review notification
                        mock_notifier.notify_manual_review.assert_called_once()
