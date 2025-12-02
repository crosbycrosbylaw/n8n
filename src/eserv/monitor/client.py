import threading
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from eserv.monitor.flags import StatusFlag
    from eserv.util import OAuthCredential
    from eserv.util.config import MonitoringConfig

    from .types import EmailRecord


class GraphClient:
    """Microsoft Graph API client for email monitoring."""

    def __init__(self, credential: OAuthCredential, config: MonitoringConfig) -> None:
        """Initialize a Microsoft Graph client."""
        self.cred = credential
        self.config = config
        self._folder_id_cache: dict[str, str] = {}
        self._lock = threading.Lock()

    def _get_headers(self) -> dict[str, str]:
        """Get authorization headers with current access token."""
        return {
            'Authorization': f'Bearer {self.cred.access_token}',
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, path: str, **kwds: Any) -> dict[str, Any]:
        """Make Graph API request."""
        url = f'{self.config.graph_api_base_url}{path}'
        headers = self._get_headers()

        response = requests.request(method, url, headers=headers, timeout=30, **kwds)
        response.raise_for_status()

        return response.json() if response.text else {}

    def resolve_monitoring_folder_id(self) -> str:
        """Resolve monitoring folder path to folder ID.

        Raises:
            FileNotFoundError: If a folder in the path does not exist.

        """
        with self._lock:
            if 'monitoring' in self._folder_id_cache:
                return self._folder_id_cache['monitoring']

        # Split path and walk hierarchy
        path_parts = self.config.folder_path.split('/')
        current_id = 'root'

        for part in path_parts:
            # GET /me/mailFolders/{parentId}/childFolders to find child with matching name
            result = self._request(
                'GET',
                path=f'/me/mailFolders/{current_id}/childFolders',
                params={'$filter': f"displayName eq '{part}'"},
            )

            folders = result.get('value', [])

            if not folders:
                raise FileNotFoundError(part)

            current_id = folders[0]['id']

        with self._lock:
            self._folder_id_cache['monitoring'] = current_id

        return current_id

    def fetch_unprocessed_emails(
        self,
        num_days: int,
        processed_uids: set[str],
    ) -> list[EmailRecord]:
        """Fetch emails from monitoring folder, exclude already-processed."""
        from .types import EmailRecord  # noqa: PLC0415

        folder_id = self.resolve_monitoring_folder_id()

        # Calculate date range
        start_date = (datetime.now(UTC) - timedelta(days=num_days)).isoformat()

        # Graph API filter: receivedDateTime >= start_date AND has attachments
        filter_expr = f'receivedDateTime ge {start_date}Z and hasAttachments eq true'

        records: list[EmailRecord] = []
        next_link: str | None = None

        # Pagination loop to fetch all matching emails
        while True:
            if next_link:
                # Use next link for subsequent pages
                # Graph API returns full URL in @odata.nextLink
                response = requests.get(next_link, headers=self._get_headers(), timeout=30)
                response.raise_for_status()
                result = response.json() if response.text else {}
            else:
                # Initial request with filter
                result = self._request(
                    'GET',
                    path=f'/me/mailFolders/{folder_id}/messages',
                    params={
                        '$filter': filter_expr,
                        '$select': 'id,from,subject,receivedDateTime,bodyPreview',
                        '$top': 50,
                    },
                )

            # Process messages from current page
            for msg in result.get('value', []):
                uid = msg['id']

                # Skip if already processed
                if uid in processed_uids:
                    continue

                # Fetch full body (HTML)
                body_result = self._request(
                    'GET',
                    path=f'/me/messages/{uid}',
                    params={'$select': 'id,bodyPreview,body'},
                )

                html_body = body_result.get('body', {}).get('content', '')

                # Validate HTML body is not empty
                if not html_body:
                    raise ValueError(f'Email {uid} has no HTML body')

                records.append(
                    EmailRecord(
                        uid=uid,
                        sender=msg.get('from', {}).get('emailAddress', {}).get('address', ''),
                        subject=msg.get('subject', ''),
                        received_at=datetime.fromisoformat(msg.get('receivedDateTime', '')),
                        html_body=html_body,
                    )
                )

            # Check for next page
            next_link = result.get('@odata.nextLink')
            if not next_link:
                break

        return records

    def apply_flag(self, email_uid: str, flag: StatusFlag) -> None:
        """Apply MAPI flag to email (thread-safe)."""
        with self._lock:
            property_patch = {'singleValueExtendedProperties': [flag]}

            self._request('PATCH', path=f'/me/messages/{email_uid}', json=property_patch)
