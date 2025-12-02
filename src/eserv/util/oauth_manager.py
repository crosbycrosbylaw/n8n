from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import orjson
import requests

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    type CredentialType = Literal['dropboxOAuth2Api', 'microsoftOutlookOAuth2Api']


@dataclass(frozen=True, slots=True)
class OAuthCredential:
    """OAuth credential with token and expiry."""

    type: CredentialType
    account: str
    client_id: str
    client_secret: str
    token_type: str
    scope: str
    access_token: str
    refresh_token: str
    expires_at: datetime | None = None


class CredentialManager:
    """Manages OAuth credentials for Dropbox and Outlook."""

    def __init__(self, credentials_path: Path) -> None:
        """Initialize the credential manager.

        Args:
            credentials_path: Path to the JSON file containing OAuth credentials.

        """
        self.credentials_path = credentials_path
        self._credentials: dict[CredentialType, OAuthCredential] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load credentials from JSON file."""
        with self.credentials_path.open('rb') as f:
            data = orjson.loads(f.read())

        for item in data:
            cred_type = item['type']
            self._credentials[cred_type] = OAuthCredential(
                type=cred_type,
                account=item['account'],
                client_id=item['client']['id'],
                client_secret=item['client']['secret'],
                token_type=item['data']['token_type'],
                scope=item['data']['scope'],
                access_token=item['data']['access_token'],
                refresh_token=item['data']['refresh_token'],
                expires_at=self._parse_expiry(item['data']),
            )

    @staticmethod
    def _parse_expiry(data: dict[str, Any]) -> datetime | None:
        """Parse expiry from token data if present."""
        if 'expires_at' in data:
            return datetime.fromisoformat(data['expires_at'])
        if 'expires_in' in data:
            # Compute from issued_at + expires_in
            issued = datetime.fromisoformat(data.get('issued_at', datetime.now(UTC).isoformat()))
            return issued + timedelta(seconds=data['expires_in'])
        return None

    def get_credential(self, cred_type: CredentialType) -> OAuthCredential:
        """Get credential by type, refreshing if expired."""
        with self._lock:
            cred = self._credentials[cred_type]

            if self._is_expired(cred):
                cred = self._refresh(cred)
                self._credentials[cred_type] = cred
                self._persist()

            return cred

    @staticmethod
    def _is_expired(cred: OAuthCredential) -> bool:
        """Check if credential needs refresh."""
        if not cred.expires_at:
            return False
        # Refresh if within 5 minutes of expiry
        return datetime.now(UTC) > (cred.expires_at - timedelta(minutes=5))

    def _refresh(self, cred: OAuthCredential) -> OAuthCredential:
        """Refresh an OAuth2 token.

        Raises:
            ValueError:
                If the type of the credential does not match any of those configured.

        """
        if cred.type == 'dropboxOAuth2Api':
            return self._refresh_dropbox(cred)
        if cred.type == 'microsoftOutlookOAuth2Api':
            return self._refresh_outlook(cred)

        message = f'Unknown credential type: {cred.type}'
        raise ValueError(message)

    @staticmethod
    def _refresh_dropbox(cred: OAuthCredential) -> OAuthCredential:
        """Refresh Dropbox access token."""
        response = requests.post(
            'https://api.dropboxapi.com/oauth2/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': cred.refresh_token,
                'client_id': cred.client_id,
                'client_secret': cred.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        tokens = response.json()

        return OAuthCredential(
            type=cred.type,
            account=cred.account,
            client_id=cred.client_id,
            client_secret=cred.client_secret,
            token_type=tokens.get('token_type', cred.token_type),
            scope=cred.scope,
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token', cred.refresh_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=tokens.get('expires_in', 3600)),
        )

    @staticmethod
    def _refresh_outlook(cred: OAuthCredential) -> OAuthCredential:
        """Refresh Outlook access token."""
        response = requests.post(
            'https://login.microsoftonline.com/common/oauth2/v2.0/token',
            data={
                'grant_type': 'refresh_token',
                'refresh_token': cred.refresh_token,
                'client_id': cred.client_id,
                'client_secret': cred.client_secret,
                'scope': cred.scope,
            },
            timeout=30,
        )
        response.raise_for_status()
        tokens = response.json()

        return OAuthCredential(
            type=cred.type,
            account=cred.account,
            client_id=cred.client_id,
            client_secret=cred.client_secret,
            token_type=tokens.get('token_type', cred.token_type),
            scope=cred.scope,
            access_token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token', cred.refresh_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=tokens.get('expires_in', 3600)),
        )

    def _persist(self) -> None:
        """Write updated credentials back to disk."""
        data = [
            {
                'type': cred.type,
                'account': cred.account,
                'client': {'id': cred.client_id, 'secret': cred.client_secret},
                'data': {
                    'token_type': cred.token_type,
                    'scope': cred.scope,
                    'access_token': cred.access_token,
                    'refresh_token': cred.refresh_token,
                    'expires_at': cred.expires_at.isoformat() if cred.expires_at else None,
                },
            }
            for cred in self._credentials.values()
        ]

        with self.credentials_path.open('wb') as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
