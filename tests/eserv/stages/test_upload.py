"""Test suite for upload.py document upload orchestration."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from rampy import test

import eserv
from eserv.types import Notifier

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from eserv.monitor.types import EmailRecord


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


@pytest.mark.skip(
    reason='Tests deprecated DocumentUploader API - needs rewrite for current upload_documents()'
)
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
        tempdir: Callable[[str], Path],
        record: EmailRecord,  # use the fixture from conftest for creating basic sample records or call eserv.record_factory directly for more granular control
    ):
        has_refresh_credentials, refresh_succeeds = params
        cache_path = tempdir('test-uploader-token-refresh') / 'index_cache.json'
        notifier = Mock(spec=Notifier)

        # Setup uploader with or without refresh credentials

        # DocumentUploader is deprecated.
        # Instead the following are exposed:
        # - eserv.config
        # - eserv.stages.upload.DropboxManager
        # - eserv.upload_documents

        if has_refresh_credentials:
            ...
        else:  # noqa: RUF047, RUF100
            ...

        if test_token_refresh:
            # Test direct token refresh call
            if not has_refresh_credentials:
                with pytest.raises(ValueError, match='not configured'):
                    ...
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

                    ...  # noqa: PIE790

                    mock_post.assert_called_once()
                else:
                    # Mock failed refresh
                    mock_post.side_effect = Exception('API Error')

                    with pytest.raises(Exception, match='API Error'):
                        ...

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

                    ...  # noqa: PIE790

                    expected_calls = 2 if refresh_succeeds else 1

                    assert mock_post.call_count == expected_calls
                    # Verify new Dropbox client was created with refreshed token
                    assert mock_dropbox_class.call_count == expected_calls

                    mock_dropbox_class.assert_called_with('refreshed_token')
            else:
                # Without refresh credentials, should raise
                with patch.object(..., 'files_list_folder') as mock_list:
                    mock_list.side_effect = ApiError(
                        request_id='test',
                        error=mock_error,
                        user_message_text='expired_access_token',
                        user_message_locale='en',
                    )

                    with pytest.raises(ApiError):
                        ...


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


@pytest.mark.skip(
    reason='Tests deprecated DocumentUploader API - needs rewrite for current upload_documents()'
)
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
        tempdir = Path(tempfile.mkdtemp())
        try:
            case_name, doc_name, match_score = params
            cache_path = tempdir / 'index_cache.json'
            notifier = Mock(spec=Notifier)

            # uploader = ...

            # Create temp PDF file
            pdf_path = tempdir / doc_name
            pdf_path.write_text('mock pdf content')

            # Mock Dropbox operations
            with (
                # patch.object(uploader, '_refresh_index_if_needed'),
                # patch.object(uploader, '_upload_file_to_dropbox'),
                # patch.object(uploader.cache, 'get_all_paths', return_value=[]),
                NotImplemented
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

                        result = eserv.upload_documents(
                            [pdf_path],
                            case_name,
                            config=NotImplemented,
                        )

                        ...  # noqa: PIE790

                        assert result.status == eserv.status.SUCCESS
                        assert len(result.uploaded_files) == 1
                        assert result.match is not None
                        assert result.match.score == match_score
                else:
                    result = eserv.upload_documents([pdf_path], case_name, config=NotImplemented)

                    assert result.status == eserv.status.MANUAL_REVIEW
                    assert len(result.uploaded_files) == 1
                    ...  # noqa: PIE790

        finally:
            shutil.rmtree(tempdir, ignore_errors=True)


@pytest.mark.skip(
    reason='verify() method removed - validation now happens implicitly during Dropbox client creation'
)
@test.scenarios(**{
    'verify credentials configured': {
        'has_access_token': True,
        'has_client_secret': True,
        'has_refresh_token': True,
        'expected_configured': True,
    },
    'missing access_token': {
        'has_access_token': False,
        'has_client_secret': True,
        'has_refresh_token': True,
        'expected_configured': False,
    },
    'missing client_secret': {
        'has_access_token': True,
        'has_client_secret': False,
        'has_refresh_token': True,
        'expected_configured': False,
    },
    'missing refresh token': {
        'has_access_token': True,
        'has_client_secret': True,
        'has_refresh_token': False,
        'expected_configured': False,
    },
})
class TestRefreshCredentialsValidation:
    def test(
        self,
        *,
        has_access_token: bool,
        has_client_secret: bool,
        has_refresh_token: bool,
        expected_configured: bool,
        tempdir: Callable[[str], Path],
        record: EmailRecord,
    ):
        from datetime import UTC, datetime, timedelta

        from eserv.stages.upload import DropboxManager
        from eserv.types import OAuthCredential

        # NOTE: This test is deprecated. The verify() method was removed during
        # credential management simplification. Validation now happens implicitly
        # when the Dropbox client is created in DropboxManager.client property.
        # See tests/eserv/util/test_oauth_manager.py for current credential tests.

        # Create mock credential with conditional fields
        credential = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='mock_id',
            client_secret='mock_secret' if has_client_secret else '',
            token_type='bearer',
            scope='files.content.write',
            access_token='mock_token' if has_access_token else '',
            refresh_token='mock_refresh' if has_refresh_token else '',
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )

        manager = DropboxManager(credential=credential)

        # verify() method no longer exists - skipped test
        ...
