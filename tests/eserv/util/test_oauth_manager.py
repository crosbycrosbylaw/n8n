"""Test suite for util/oauth_manager.py OAuth credential management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import orjson
import pytest
import requests

from eserv.util.oauth_manager import (
    CredentialManager,
    OAuthCredential,
    _refresh_dropbox,  # noqa: PLC2701
    _refresh_outlook,  # noqa: PLC2701
)

if TYPE_CHECKING:
    from pathlib import Path


class TestTokenRefresh:
    """Test unified refresh mechanism for both Dropbox and Outlook."""

    def test_refresh_dropbox_success(self):
        """Test successful Dropbox token refresh."""
        # Create test credential
        cred = OAuthCredential(
            type='dropbox',
            account='test-business',
            client_id='test_client_id',
            client_secret='test_client_secret',
            token_type='bearer',
            scope='files.content.write',
            access_token='old_access_token',
            refresh_token='test_refresh_token',
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            handler=_refresh_dropbox,
        )

        # Mock API response
        mock_response_data = {
            'access_token': 'new_access_token',
            'token_type': 'bearer',
            'expires_in': 3600,
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Call refresh handler
            result = _refresh_dropbox(cred)

            # Assert requests.post called with correct params
            mock_post.assert_called_once_with(
                'https://api.dropbox.com/oauth2/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': 'test_refresh_token',
                    'client_id': 'test_client_id',
                    'client_secret': 'test_client_secret',
                },
                timeout=30,
            )

            # Assert correct response returned
            assert result == mock_response_data
            assert result['access_token'] == 'new_access_token'

    def test_refresh_outlook_success(self):
        """Test successful Outlook token refresh."""
        # Create test credential
        cred = OAuthCredential(
            type='microsoft-outlook',
            account='test-account',
            client_id='outlook_client_id',
            client_secret='outlook_client_secret',
            token_type='bearer',
            scope='Mail.Read offline_access',
            access_token='old_outlook_token',
            refresh_token='outlook_refresh_token',
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # Expired
            handler=_refresh_outlook,
        )

        # Mock API response
        mock_response_data = {
            'access_token': 'new_outlook_token',
            'token_type': 'bearer',
            'scope': 'Mail.Read offline_access',
            'expires_in': 3600,
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Call refresh handler
            result = _refresh_outlook(cred)

            # Assert requests.post called with correct params
            mock_post.assert_called_once_with(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': 'outlook_refresh_token',
                    'client_id': 'outlook_client_id',
                    'client_secret': 'outlook_client_secret',
                    'scope': 'Mail.Read offline_access',
                },
                timeout=30,
            )

            # Assert correct response returned
            assert result == mock_response_data
            assert result['access_token'] == 'new_outlook_token'

    def test_refresh_dropbox_network_error(self):
        """Test refresh handles network errors gracefully."""
        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='token',
            refresh_token='refresh',
            handler=_refresh_dropbox,
        )

        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError('Network error')

            with pytest.raises(requests.ConnectionError):
                _refresh_dropbox(cred)

    def test_refresh_dropbox_http_error(self):
        """Test refresh handles HTTP errors gracefully."""
        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='token',
            refresh_token='invalid_refresh',
            handler=_refresh_dropbox,
        )

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.HTTPError('401 Unauthorized')
            mock_post.return_value = mock_response

            with pytest.raises(requests.HTTPError):
                _refresh_dropbox(cred)

    def test_credential_refresh_integration(self):
        """Test OAuthCredential.refresh() uses handler correctly."""
        # Create credential with mocked handler
        mock_handler = Mock(return_value={'access_token': 'new_token', 'expires_in': 3600})

        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='old_token',
            refresh_token='refresh',
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            handler=mock_handler,
        )

        # Call refresh
        refreshed = cred.refresh()

        # Assert handler was called
        mock_handler.assert_called_once_with(cred)

        # Assert new credential returned
        assert refreshed.access_token == 'new_token'
        assert refreshed.expires_at is not None
        assert refreshed.expires_at > datetime.now(UTC)

    def test_refresh_without_handler_raises_error(self):
        """Test that refresh without handler raises ValueError."""
        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='token',
            refresh_token='refresh',
            handler=None,  # No handler
        )

        with pytest.raises(ValueError, match='no configuration set'):
            cred.refresh()


class TestCredentialUpdate:
    """Test credential update logic."""

    def test_update_from_refresh_with_expires_in(self):
        """Test updating credential from token data with expires_in."""
        # Create original credential
        original = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='old_token',
            refresh_token='old_refresh',
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        # Update with new token data
        token_data = {
            'access_token': 'new_token',
            'refresh_token': 'new_refresh',
            'expires_in': 3600,
        }

        updated = original.update_from_refresh(token_data)

        # Assert new credential returned with correct values
        assert updated.access_token == 'new_token'
        assert updated.refresh_token == 'new_refresh'
        assert updated.expires_at is not None
        assert updated.expires_at > datetime.now(UTC)
        assert updated.expires_at < datetime.now(UTC) + timedelta(hours=2)

        # Assert original unchanged (immutable pattern)
        assert original.access_token == 'old_token'
        assert original.refresh_token == 'old_refresh'

    def test_update_from_refresh_with_expires_at(self):
        """Test updating credential with expires_at timestamp."""
        original = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='old_token',
            refresh_token='refresh',
        )

        future_time = datetime.now(UTC) + timedelta(hours=2)
        token_data = {
            'access_token': 'new_token',
            'expires_at': future_time.isoformat(),
        }

        updated = original.update_from_refresh(token_data)

        assert updated.access_token == 'new_token'
        assert updated.expires_at == future_time

    def test_update_preserves_unchanged_fields(self):
        """Test that fields not in token data are preserved."""
        original = OAuthCredential(
            type='dropbox',
            account='original_account',
            client_id='original_client',
            client_secret='original_secret',
            token_type='bearer',
            scope='files.content.write',
            access_token='old_token',
            refresh_token='original_refresh',
        )

        # Update with minimal data (only access_token)
        token_data = {
            'access_token': 'new_token',
            'expires_in': 3600,
        }

        updated = original.update_from_refresh(token_data)

        # Assert updated field changed
        assert updated.access_token == 'new_token'

        # Assert other fields preserved
        assert updated.account == 'original_account'
        assert updated.client_id == 'original_client'
        assert updated.client_secret == 'original_secret'
        assert updated.scope == 'files.content.write'
        assert updated.refresh_token == 'original_refresh'

    def test_update_with_partial_data(self):
        """Test update with only some fields in token response."""
        original = OAuthCredential(
            type='microsoft-outlook',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='Mail.Read',
            access_token='old_token',
            refresh_token='refresh',
        )

        # Outlook might return scope in refresh response
        token_data = {
            'access_token': 'new_token',
            'scope': 'Mail.Read Mail.Send',
            'expires_in': 3600,
        }

        updated = original.update_from_refresh(token_data)

        assert updated.access_token == 'new_token'
        assert updated.scope == 'Mail.Read Mail.Send'
        assert updated.refresh_token == 'refresh'  # Unchanged

    def test_update_immutability(self):
        """Test that update_from_refresh follows immutable pattern."""
        original = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='token1',
            refresh_token='refresh',
        )

        # Multiple updates should create new instances
        updated1 = original.update_from_refresh({'access_token': 'token2', 'expires_in': 3600})
        updated2 = updated1.update_from_refresh({'access_token': 'token3', 'expires_in': 3600})

        # All should be different objects
        assert original is not updated1
        assert updated1 is not updated2
        assert original is not updated2

        # Each should have correct value
        assert original.access_token == 'token1'
        assert updated1.access_token == 'token2'
        assert updated2.access_token == 'token3'


class TestDropboxManager:
    """Test DropboxManager client creation and lifecycle."""

    def test_client_created_lazily(self):
        """Test client is created only when accessed."""
        from eserv.stages.upload import DropboxManager

        # Create credential
        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='test_client_id',
            client_secret='test_client_secret',
            token_type='bearer',
            scope='files.content.write',
            access_token='test_access_token',
            refresh_token='test_refresh_token',
        )

        # Create manager
        manager = DropboxManager(cred)

        # Assert _client is None initially
        assert manager._client is None

        # Access client property
        with patch('dropbox.Dropbox') as MockDropbox:  # noqa: N806
            mock_client = Mock()
            MockDropbox.return_value = mock_client

            client = manager.client

            # Assert Dropbox constructor called with correct params
            MockDropbox.assert_called_once_with(
                oauth2_access_token='test_access_token',
                oauth2_refresh_token='test_refresh_token',
                app_key='test_client_id',
                app_secret='test_client_secret',
            )

            # Assert client instance stored
            assert manager._client is mock_client
            assert client is mock_client

    def test_client_reused_on_subsequent_access(self):
        """Test client is reused across accesses."""
        from eserv.stages.upload import DropboxManager

        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='token',
            refresh_token='refresh',
        )

        manager = DropboxManager(cred)

        with patch('dropbox.Dropbox') as MockDropbox:  # noqa: N806
            mock_client = Mock()
            MockDropbox.return_value = mock_client

            # Access client twice
            client1 = manager.client
            client2 = manager.client

            # Assert Dropbox constructor called only once
            assert MockDropbox.call_count == 1

            # Assert same instance returned
            assert client1 is client2
            assert client1 is mock_client

    def test_manager_uses_credential_values(self):
        """Test that DropboxManager uses credential's current values."""
        from eserv.stages.upload import DropboxManager

        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='original_client_id',
            client_secret='original_secret',
            token_type='bearer',
            scope='files',
            access_token='original_token',
            refresh_token='original_refresh',
        )

        manager = DropboxManager(cred)

        with patch('dropbox.Dropbox') as MockDropbox:  # noqa: N806
            _ = manager.client

            # Verify original credential values were used
            call_kwargs = MockDropbox.call_args.kwargs
            assert call_kwargs['oauth2_access_token'] == 'original_token'
            assert call_kwargs['oauth2_refresh_token'] == 'original_refresh'
            assert call_kwargs['app_key'] == 'original_client_id'
            assert call_kwargs['app_secret'] == 'original_secret'


class TestCredentialSerialization:
    """Test credential serialization (export/load)."""

    def test_export_flat_format(self):
        """Test credential exports to flat JSON format."""
        cred = OAuthCredential(
            type='dropbox',
            account='business',
            client_id='test_client_id',
            client_secret='test_client_secret',
            token_type='bearer',
            scope='files.content.write',
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            expires_at=datetime(2025, 12, 3, 12, 0, 0, tzinfo=UTC),
        )

        exported = cred.export()

        # Assert flat structure
        assert exported['type'] == 'dropbox'
        assert exported['account'] == 'business'
        assert exported['client_id'] == 'test_client_id'
        assert exported['client_secret'] == 'test_client_secret'
        assert exported['token_type'] == 'bearer'
        assert exported['scope'] == 'files.content.write'
        assert exported['access_token'] == 'test_access_token'
        assert exported['refresh_token'] == 'test_refresh_token'
        assert exported['expires_at'] == '2025-12-03T12:00:00+00:00'

        # Assert no nested dicts
        assert 'client' not in exported
        assert 'data' not in exported

        # Assert no handler field
        assert 'handler' not in exported

    def test_export_without_expires_at(self):
        """Test export handles missing expires_at."""
        cred = OAuthCredential(
            type='dropbox',
            account='test',
            client_id='client',
            client_secret='secret',
            token_type='bearer',
            scope='files',
            access_token='token',
            refresh_token='refresh',
            expires_at=None,  # No expiration
        )

        exported = cred.export()

        assert 'expires_at' in exported
        assert exported['expires_at'] is None


class TestCredentialManager:
    """Test credential manager loading and expiry checking."""

    def test_load_credentials_flat_format(self, tempdir: Path):
        """Test loading credentials from flat JSON format."""
        # Create test credentials file with flat format
        creds_file = tempdir / 'credentials.json'
        test_data = [
            {
                'type': 'dropbox',
                'account': 'business',
                'client_id': 'dbx_client',
                'client_secret': 'dbx_secret',
                'token_type': 'bearer',
                'scope': 'files.content.write',
                'access_token': 'dbx_access',
                'refresh_token': 'dbx_refresh',
                'expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        ]

        with creds_file.open('wb') as f:
            f.write(orjson.dumps(test_data))

        # Load credentials
        manager = CredentialManager(creds_file)

        # Assert credential loaded correctly
        cred = manager.get_credential('dropbox')
        assert cred.type == 'dropbox'
        assert cred.account == 'business'
        assert cred.client_id == 'dbx_client'
        assert cred.client_secret == 'dbx_secret'
        assert cred.access_token == 'dbx_access'
        assert cred.refresh_token == 'dbx_refresh'
        assert cred.handler is not None

    def test_get_credential_refreshes_when_expired(self, tempdir: Path):
        """Test that get_credential auto-refreshes expired tokens."""
        # Create credentials with past expiry (flat format)
        creds_file = tempdir / 'credentials.json'
        test_data = [
            {
                'type': 'dropbox',
                'account': 'test',
                'client_id': 'client',
                'client_secret': 'secret',
                'token_type': 'bearer',
                'scope': 'files',
                'access_token': 'old_token',
                'refresh_token': 'refresh',
                'expires_at': (datetime.now(UTC) - timedelta(hours=1)).isoformat(),  # Expired
            },
        ]

        with creds_file.open('wb') as f:
            f.write(orjson.dumps(test_data))

        manager = CredentialManager(creds_file)

        # Mock requests.post for token refresh
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'access_token': 'new_token',
                'expires_in': 3600,
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            # Get credential (should trigger refresh)
            cred = manager.get_credential('dropbox')

            # Assert refresh was called
            assert mock_post.called
            assert cred.access_token == 'new_token'

    def test_get_credential_no_refresh_when_valid(self, tempdir: Path):
        """Test that get_credential doesn't refresh valid tokens."""
        # Create credentials with future expiry (flat format)
        creds_file = tempdir / 'credentials.json'
        test_data = [
            {
                'type': 'dropbox',
                'account': 'test',
                'client_id': 'client',
                'client_secret': 'secret',
                'token_type': 'bearer',
                'scope': 'files',
                'access_token': 'valid_token',
                'refresh_token': 'refresh',
                'expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        ]

        with creds_file.open('wb') as f:
            f.write(orjson.dumps(test_data))

        manager = CredentialManager(creds_file)

        # Mock refresh handler
        with patch('eserv.util.oauth_manager._refresh_dropbox') as mock_refresh:
            # Get credential (should NOT trigger refresh)
            cred = manager.get_credential('dropbox')

            # Assert refresh was NOT called
            assert not mock_refresh.called
            assert cred.access_token == 'valid_token'

    def test_persist_saves_flat_format(self, tempdir: Path):
        """Test that persist() saves credentials in flat format."""
        # Create initial credentials (flat format)
        creds_file = tempdir / 'credentials.json'
        test_data = [
            {
                'type': 'dropbox',
                'account': 'test',
                'client_id': 'client',
                'client_secret': 'secret',
                'token_type': 'bearer',
                'scope': 'files',
                'access_token': 'old_token',
                'refresh_token': 'refresh',
            },
        ]

        with creds_file.open('wb') as f:
            f.write(orjson.dumps(test_data))

        manager = CredentialManager(creds_file)

        # Simulate token refresh by manually updating credential
        from dataclasses import replace

        cred = manager._credentials['dropbox']
        updated_cred = replace(cred, access_token='new_token')
        manager._credentials['dropbox'] = updated_cred

        # Persist changes
        manager.persist()

        # Reload and verify flat format
        with creds_file.open('rb') as f:
            saved_data = orjson.loads(f.read())

        # Assert flat structure
        assert saved_data[0]['access_token'] == 'new_token'
        assert saved_data[0]['type'] == 'dropbox'
        assert saved_data[0]['client_id'] == 'client'

        # Assert no nested dicts
        assert 'client' not in saved_data[0]
        assert 'data' not in saved_data[0]
