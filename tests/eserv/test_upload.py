"""Test suite for upload.py document upload orchestration."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from rampy import test

from eserv.upload import DocumentUploader, UploadStatus
from eserv.util.notifications import Notifier

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Any


@pytest.fixture
def temp_dir() -> Generator[Path]:
    path = test.directory('test-upload')

    try:
        yield path
    finally:
        path.clean()


def scenario(
    *,
    has_refresh_credentials: bool = True,
    refresh_succeeds: bool = True,
    test_token_refresh: bool = False,
    test_expired_token: bool = False,
) -> dict[str, Any]:
    """Create test scenario for DocumentUploader token refresh."""
    return {
        'params': [has_refresh_credentials, refresh_succeeds],
        'test_token_refresh': test_token_refresh,
        'test_expired_token': test_expired_token,
    }


@test.scenarios(**{
    'successful token refresh': scenario(
        has_refresh_credentials=True,
        refresh_succeeds=True,
        test_token_refresh=True,
    ),
    'token refresh without credentials': scenario(
        has_refresh_credentials=False,
        test_token_refresh=True,
    ),
    'token refresh API failure': scenario(
        has_refresh_credentials=True,
        refresh_succeeds=False,
        test_token_refresh=True,
    ),
    'expired token triggers auto-refresh': scenario(
        has_refresh_credentials=True,
        refresh_succeeds=True,
        test_expired_token=True,
    ),
    'expired token without refresh creds': scenario(
        has_refresh_credentials=False,
        test_expired_token=True,
    ),
})
class TestDocumentUploaderTokenRefresh:
    def test(
        self,
        /,
        params: list[bool],
        test_token_refresh: bool,
        test_expired_token: bool,
        temp_dir: Path,
    ):

        has_refresh_credentials, refresh_succeeds = params
        cache_path = temp_dir / 'index_cache.json'
        notifier = Mock(spec=Notifier)

        # Setup uploader with or without refresh credentials
        if has_refresh_credentials:
            uploader = DocumentUploader(
                cache_path=cache_path,
                dbx_token='mock_token',
                notifier=notifier,
                manual_review_folder='/Manual Review',
                dbx_app_key='mock_app_key',
                dbx_app_secret='mock_app_secret',
                dbx_refresh_token='mock_refresh_token',
            )
        else:
            uploader = DocumentUploader(
                cache_path=cache_path,
                dbx_token='mock_token',
                notifier=notifier,
                manual_review_folder='/Manual Review',
            )

        if test_token_refresh:
            # Test direct token refresh call
            if not has_refresh_credentials:
                with pytest.raises(ValueError, match='not configured'):
                    uploader._refresh_access_token()
                return

            # Mock successful refresh
            with patch('requests.post') as mock_post:
                if refresh_succeeds:
                    mock_response = Mock()
                    mock_response.json.return_value = {
                        'access_token': 'new_mock_token',
                    }
                    mock_response.raise_for_status = Mock()
                    mock_post.return_value = mock_response

                    new_token = uploader._refresh_access_token()

                    assert new_token == 'new_mock_token'
                    assert uploader.dbx_token == 'new_mock_token'
                    mock_post.assert_called_once()
                else:
                    # Mock failed refresh
                    mock_post.side_effect = Exception('API Error')

                    with pytest.raises(Exception, match='API Error'):
                        uploader._refresh_access_token()

        elif test_expired_token:
            # Test auto-refresh on expired token error
            from dropbox.exceptions import ApiError

            # Create mock error that str() will return the expired token message
            mock_error = Mock()
            mock_error.__str__ = Mock(return_value='Error: expired_access_token')

            if has_refresh_credentials:
                with (
                    patch('requests.post') as mock_post,
                    patch('eserv.upload.Dropbox') as mock_dropbox_class,
                ):
                    # Mock refresh token response
                    mock_response = Mock()
                    mock_response.json.return_value = {
                        'access_token': 'refreshed_token',
                    }
                    mock_response.raise_for_status = Mock()
                    mock_post.return_value = mock_response

                    # Create mock Dropbox instances
                    mock_dbx_expired = Mock()
                    mock_dbx_refreshed = Mock()

                    # First Dropbox instance (expired token) - raises error
                    mock_dbx_expired.files_list_folder.side_effect = ApiError(
                        request_id='test',
                        error=mock_error,
                        user_message_text='expired_access_token',
                        user_message_locale='en',
                    )

                    # Second Dropbox instance (refreshed token) - succeeds
                    mock_dbx_refreshed.files_list_folder.return_value = Mock(
                        entries=[],
                        has_more=False,
                    )

                    # Mock Dropbox constructor to return different instances
                    mock_dropbox_class.side_effect = [mock_dbx_expired, mock_dbx_refreshed]

                    # Re-initialize uploader to use mocked Dropbox
                    uploader.dbx = mock_dbx_expired

                    # This should trigger auto-refresh
                    uploader._refresh_index_if_needed()

                    # Verify token was refreshed
                    assert uploader.dbx_token == 'refreshed_token'

                    expected_calls = 2 if refresh_succeeds else 1

                    assert mock_post.call_count == expected_calls
                    # Verify new Dropbox client was created with refreshed token
                    assert mock_dropbox_class.call_count == expected_calls

                    mock_dropbox_class.assert_called_with('refreshed_token')
            else:
                # Without refresh credentials, should raise
                with patch.object(uploader.dbx, 'files_list_folder') as mock_list:
                    mock_list.side_effect = ApiError(
                        request_id='test',
                        error=mock_error,
                        user_message_text='expired_access_token',
                        user_message_locale='en',
                    )

                    with pytest.raises(ApiError):
                        uploader._refresh_index_if_needed()


def upload_scenario(
    *,
    case_name: str | None = 'Test Case',
    doc_name: str = 'test_doc.pdf',
    match_score: float = 85.0,
    manual_review: bool = False,
) -> dict[str, Any]:
    """Create test scenario for document upload."""
    return {
        'params': [case_name, doc_name, match_score],
        'manual_review': manual_review,
    }


@test.scenarios(**{
    'successful upload': upload_scenario(
        case_name='Client Matter',
        doc_name='document.pdf',
        match_score=90.0,
    ),
    'manual review - no case name': upload_scenario(
        case_name=None,
        manual_review=True,
    ),
    'manual review - low match score': upload_scenario(
        case_name='Ambiguous Case',
        match_score=50.0,
        manual_review=True,
    ),
})
class TestDocumentUpload:
    def test(
        self,
        /,
        params: list[Any],
        manual_review: bool,
    ):
        temp_dir = Path(tempfile.mkdtemp())
        try:
            case_name, doc_name, match_score = params
            cache_path = temp_dir / 'index_cache.json'
            notifier = Mock(spec=Notifier)

            uploader = DocumentUploader(
                cache_path=cache_path,
                dbx_token='mock_token',
                notifier=notifier,
                manual_review_folder='/Manual Review',
                min_match_score=70.0,
            )

            # Create temp PDF file
            pdf_path = temp_dir / doc_name
            pdf_path.write_text('mock pdf content')

            # Mock Dropbox operations
            with (
                patch.object(uploader, '_refresh_index_if_needed'),
                patch.object(uploader, '_upload_file_to_dropbox'),
                patch.object(uploader.cache, 'get_all_paths', return_value=[]),
            ):
                # Mock folder matching
                if case_name and not manual_review:
                    with patch('eserv.upload.FolderMatcher.find_best_match') as mock_match:
                        from eserv.util.target_finder import CaseMatch

                        mock_match.return_value = CaseMatch(
                            folder_path=f'/Clio/{case_name}',
                            matched_on=case_name,
                            score=match_score,
                        )

                        result = uploader.process_document(case_name, documents=[pdf_path])

                        assert result.status == UploadStatus.SUCCESS
                        assert len(result.uploaded_files) == 1
                        assert result.match is not None
                        assert result.match.score == match_score
                else:
                    result = uploader.process_document(case_name, documents=[pdf_path])

                    assert result.status == UploadStatus.MANUAL_REVIEW
                    assert len(result.uploaded_files) == 1
                    assert uploader.manual_review_folder in result.folder_path

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


@test.scenarios(**{
    'verify credentials configured': {
        'has_app_key': True,
        'has_app_secret': True,
        'has_refresh_token': True,
        'expected_configured': True,
    },
    'missing app key': {
        'has_app_key': False,
        'has_app_secret': True,
        'has_refresh_token': True,
        'expected_configured': False,
    },
    'missing app secret': {
        'has_app_key': True,
        'has_app_secret': False,
        'has_refresh_token': True,
        'expected_configured': False,
    },
    'missing refresh token': {
        'has_app_key': True,
        'has_app_secret': True,
        'has_refresh_token': False,
        'expected_configured': False,
    },
})
class TestRefreshCredentialsValidation:
    def test(
        self,
        *,
        has_app_key: bool,
        has_app_secret: bool,
        has_refresh_token: bool,
        expected_configured: bool,
        temp_dir: Path,
    ):

        cache_path = temp_dir.joinpath('index_cache.json')
        notifier = Mock(spec=Notifier)

        uploader = DocumentUploader(
            cache_path=cache_path,
            dbx_token='mock_token',
            notifier=notifier,
            manual_review_folder='/Manual Review',
            dbx_app_key='app_key' if has_app_key else None,
            dbx_app_secret='app_secret' if has_app_secret else None,
            dbx_refresh_token='refresh_token' if has_refresh_token else None,
        )

        # Test that credentials check works correctly
        has_credentials = all([
            uploader.dbx_app_key,
            uploader.dbx_app_secret,
            uploader.dbx_refresh_token,
        ])

        assert has_credentials == expected_configured

        if not expected_configured:
            with pytest.raises(ValueError, match='not configured'):
                uploader._refresh_access_token()
