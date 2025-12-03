from __future__ import annotations

import threading
from collections.abc import Mapping
from dataclasses import InitVar, asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Self

import orjson
import requests
from rampy.util import create_field_factory

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence
    from pathlib import Path
    from typing import Literal

    from dropbox import Dropbox
    from requests import Response

    from eserv.monitor.client import GraphClient

    type CredentialType = Literal['dropbox', 'microsoft-outlook']


def _refresh_dropbox(cred: OAuthCredential[Dropbox]) -> OAuthCredential[Dropbox]:
    from dropbox import Dropbox  # noqa: PLC0415

    if not cred.has_client():
        dropbox = Dropbox(
            oauth2_refresh_token=cred.refresh_token,
            app_key=cred.client_id,
            app_secret=cred.client_secret,
        )
        cred.set_client(dropbox)

    client = cred.get_client()
    client.check_and_refresh_access_token()

    return cred.object_hook({
        'access_token': getattr(client, '_oauth2_access_token', cred.access_token),
        'expires_in': getattr(client, '_oauth2_access_token_expiration', 3600),
    })


def _refresh_outlook(cred: OAuthCredential[GraphClient]) -> OAuthCredential[GraphClient]:

    config = RefreshConfig(
        endpoint='https://login.microsoftonline.com/common/oauth2/v2.0/token',
        extend_keys=['scope'],
    )

    return config.post(asdict(cred)).json(object_hook=cred.object_hook)


@dataclass(slots=True)
class RefreshConfig:
    """Configuration for token refresh requests."""

    endpoint: str

    extend_keys: InitVar[Sequence[str]] = ()

    keys: set[str] = field(
        init=False,
        default_factory=lambda: {
            'refresh_token',
            'client_id',
            'client_secret',
        },
    )
    data: dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(
        self,
        extend_keys: Sequence[str],
    ) -> None:
        """Update the data field names to include defaults."""
        if extend_keys:
            self.keys.update(extend_keys)

    @property
    def _missing_fields(self) -> Generator[str]:
        yield from (x for x in self.keys if x not in self.data)

    def _verify_data(self) -> dict[str, Any]:
        if name := next(self._missing_fields, None):
            message = f"Refresh request missing required field: '{name}'"
            raise ValueError(message)

        self.data['grant_type'] = 'refresh_token'
        return self.data

    def post(self, mapping: Mapping[str, Any]) -> Response:
        """Send token refresh request to the configured endpoint.

        Returns:
            Response object from the refresh request.

        """
        self.data.update(x for x in mapping.items() if x[0] in self.keys)
        response = requests.post(self.endpoint, data=self._verify_data(), timeout=30)
        response.raise_for_status()

        return response


@dataclass(slots=True)
class OAuthCredential[T = Any]:
    """OAuth credential with token and expiry.

    The string representation of an `OAuthCredential` evaluates to it's access token.
    """

    type: CredentialType
    account: str
    client_id: str
    client_secret: str
    token_type: str
    scope: str
    access_token: str
    refresh_token: str
    expires_at: datetime | None = None

    client: T | None = field(init=False, default=None, repr=False)

    def has_client(self) -> bool:
        """Check if a client is set for this credential.

        Returns:
            True if exactly one client is set, False otherwise.

        """
        return self.client is not None

    def get_client(self) -> T:
        """Get the client for this credential.

        Returns:
            The client instance associated with this credential.

        Raises:
            ValueError:
                If there is no client configured when this method is called.

        """
        if client := self.client:
            return client

        message = 'There is no client configured for this credential.'
        raise ValueError(message)

    def set_client(self, client: T) -> None:
        """Set the client for this credential.

        Args:
            client: The client instance to associate with this credential.

        """
        self.client = client

    handler: Callable[[OAuthCredential], OAuthCredential] | None = field(default=None, repr=False)

    def __str__(self) -> str:
        """Return the access token as string representation."""
        return self.access_token

    def export(self) -> dict[str, Any]:
        """Convert credential to JSON serializable dictionary with standardized format.

        Returns:
            Dictionary with 'type', 'account', 'client', and 'data' top-level keys.

        """
        out: dict[str, Any] = {'data': {}, 'client': {}}

        for key, val in asdict(self).items():
            if key in {'type', 'account'}:
                out[key] = val
            elif key.startswith('client_'):
                out['client'][key.removeprefix('client_')] = val
            elif isinstance(val, datetime):
                out['data'][key] = val.isoformat()
            else:
                out['data'][key] = val

        return out

    def refresh(self) -> OAuthCredential:
        """Create a new credential with updated token information.

        Returns:
            New OAuthCredential instance with updated token information.

        Raises:
            ValueError:
                If the `handler` property for this instance has not been set.

        """
        if self.handler is None:
            message = 'There is no configuration set for this credential.'
            raise ValueError(message)

        if isinstance(self.handler, RefreshConfig):
            response = self.handler.post(asdict(self))
            return response.json(object_hook=self.object_hook)

        return self.handler(self)

    def object_hook(self, obj: dict[str, Any]) -> Self:
        """Return this credential with information updated from the given dictionary."""
        expiration_key = next((key for key in obj if key.startswith('expires_')), None)
        expiration = obj.pop(expiration_key, 3600) if expiration_key else 3600

        if isinstance(expiration, datetime):
            self.expires_at = expiration
        elif isinstance(expiration, int | float):
            self.expires_at = datetime.now(UTC) + timedelta(seconds=expiration)

        for key, value in obj.items():
            if key in {'token_type', 'scope', 'access_token', 'refresh_token'} and value:
                setattr(self, key, value)

        return self


class CredentialManager:
    """Manages OAuth credentials for Dropbox and Outlook."""

    def __init__(self, json_path: Path) -> None:
        """Initialize the credential manager.

        Args:
            json_path: Path to the JSON file containing OAuth credentials.

        """
        self.credentials_path = json_path
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
                **{k: v for k, v in item.items() if k in {'type', 'account'}},
                **{f'client_{k}': v for k, v in item['client'].items()},
                **{
                    k: v
                    for k, v in item['data'].items()
                    if k in {'token_type', 'scope', 'access_token', 'refresh_token'}
                },
                expires_at=self._parse_expiry(item['data']),
                handler=self._resolve_refresh_handler(cred_type),
            )

    @staticmethod
    def _resolve_refresh_handler(
        cred_type: str,
    ) -> Callable[[OAuthCredential], OAuthCredential] | None:
        match cred_type:
            case 'dropbox':
                return _refresh_dropbox
            case 'microsoft-outlook':
                return _refresh_outlook

        return None

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
                self.persist()

            return cred

    @staticmethod
    def _is_expired(cred: OAuthCredential) -> bool:
        """Check if credential needs refresh."""
        if not cred.expires_at:
            return False
        # Refresh if within 5 minutes of expiry
        return datetime.now(UTC) > (cred.expires_at - timedelta(minutes=5))

    @staticmethod
    def _refresh(cred: OAuthCredential) -> OAuthCredential:
        """Refresh an OAuth2 token.

        Raises:
            ValueError:
                If the type of the credential does not match any of those configured.

        """
        if cred.handler is None:
            message = f'Unknown credential type: {cred.type}'
            raise ValueError(message)

        return cred.refresh()

    def persist(self) -> None:
        """Write updated credentials back to disk."""
        data: list[dict[str, Any]] = [cred.export() for cred in self._credentials.values()]

        with self.credentials_path.open('wb') as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


if TYPE_CHECKING:

    def credential_manager(json_path: Path) -> CredentialManager:
        """Initialize the credential manager.

        Args:
            json_path: Path to the JSON file containing OAuth credentials.

        """
        ...


credential_manager = create_field_factory(CredentialManager)
