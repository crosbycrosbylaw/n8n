"""Application configuration loaded from environment variables.

Provides nested dataclasses for scoped configuration (SMTP, Dropbox, etc.)
with validation, type coercion, and sensible development defaults.

Uses python-dotenv to load .env files and validates all required fields
and formats at application startup.

Classes:
    SMTPConfig: Email delivery configuration.
    DropboxConfig: Dropbox API configuration.
    PathsConfig: File storage paths.
    EmailStateConfig: Email state tracking configuration.
    CacheConfig: Cache configuration.
    Config: Root configuration with all nested scopes.

"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rampy import console


class _MissingVariableError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(f'{name} environment variable is required')


class _InvalidFormatError(ValueError):
    def __init__(self, name: str, value: str) -> None:
        super().__init__(f'Invalid {name} format: {value}')


@dataclass(slots=True, frozen=True)
class SMTPConfig:
    """SMTP configuration for email notifications.

    Attributes:
        server: SMTP server hostname.
        port: SMTP port (typically 587 for TLS).
        from_addr: Sender email address.
        to_addr: Recipient email address.
        username: SMTP username (optional if not requiring authentication).
        password: SMTP password or app-specific password.
        use_tls: Whether to use TLS encryption.

    """

    server: str
    port: int
    from_addr: str
    to_addr: str
    username: str | None = None
    password: str | None = None
    use_tls: bool = True

    @classmethod
    def from_env(cls) -> SMTPConfig:
        """Load SMTP configuration from environment variables.

        Raises:
            TypeError: If the value recieved for the `port` is not an integer.
            _MissingVariableError: If required fields are missing.
            _InvalidFormatError: If any variable values are of an invalid format.

        """
        server = os.getenv('SMTP_SERVER')
        port_str = os.getenv('SMTP_PORT', '587')
        from_addr = os.getenv('SMTP_FROM_ADDR')
        to_addr = os.getenv('SMTP_TO_ADDR')
        username = os.getenv('SMTP_USERNAME')
        password = os.getenv('SMTP_PASSWORD')
        use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() in {'true', '1', 'yes'}

        if not server:
            raise _MissingVariableError(name='SMTP_SERVER')
        if not from_addr:
            raise _MissingVariableError(name='SMTP_FROM_ADDR')
        if not to_addr:
            raise _MissingVariableError(name='SMTP_TO_ADDR')

        try:
            port = int(port_str)
        except ValueError as e:
            message = f'SMTP_PORT must be an integer string, got: {port_str}'
            raise TypeError(message) from e

        # Validate email format

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        if not email_pattern.match(from_addr):
            raise _InvalidFormatError(name='SMTP_FROM_ADDR', value=from_addr)
        if not email_pattern.match(to_addr):
            raise _InvalidFormatError(name='SMTP_TO_ADDR', value=to_addr)

        return cls(
            server=server,
            port=port,
            from_addr=from_addr,
            to_addr=to_addr,
            username=username,
            password=password,
            use_tls=use_tls,
        )


@dataclass(slots=True, frozen=True)
class DropboxConfig:
    """Dropbox API configuration.

    Attributes:
        token: Dropbox API access token.

    """

    token: str

    @classmethod
    def from_env(cls) -> DropboxConfig:
        """Load Dropbox configuration from environment variables.

        Raises:
            _MissingVariableError: If token is missing.

        """
        if not (token := os.getenv('DROPBOX_TOKEN')):
            raise _MissingVariableError(name='DROPBOX_TOKEN')

        return cls(token=token)


@dataclass(slots=True, frozen=True)
class PathsConfig:
    """File storage paths.

    Attributes:
        service_dir: Directory for service data (state, cache, logs).
        manual_review_folder: Dropbox folder path for manual review uploads.

    """

    service_dir: Path
    manual_review_folder: str

    @classmethod
    def from_env(cls) -> PathsConfig:
        """Load paths configuration from environment variables.

        Raises:
            _MissingVariableError: If required paths are missing.

        """
        if not (manual_review := os.getenv('MANUAL_REVIEW_FOLDER')):
            raise _MissingVariableError(name='MANUAL_REVIEW_FOLDER')

        if path_string := os.getenv('SERVICE_DIR'):
            service_dir = Path(path_string).resolve()
            service_dir.mkdir(parents=True, exist_ok=True)
        else:
            from rampy import rootpath  # noqa: PLC0415

            service_dir = rootpath('service', mkdir=True)

        return cls(service_dir=service_dir, manual_review_folder=manual_review)


@dataclass(slots=True, frozen=True)
class EmailStateConfig:
    """Email state tracking configuration.

    Attributes:
        state_file: Path to email state JSON file.

    """

    state_file: Path

    @classmethod
    def from_env(cls, service_dir: Path) -> EmailStateConfig:
        """Load email state configuration.

        Args:
            service_dir: Service directory from PathsConfig.

        """
        return cls(state_file=service_dir / 'email_state.json')


@dataclass(slots=True, frozen=True)
class CacheConfig:
    """Cache configuration.

    Attributes:
        index_file: Path to Dropbox index cache file.
        ttl_hours: Cache time-to-live in hours.

    """

    index_file: Path
    ttl_hours: int

    @classmethod
    def from_env(cls, service_dir: Path) -> CacheConfig:
        """Load cache configuration from environment variables.

        Args:
            service_dir: Service directory from PathsConfig.

        Raises:
            TypeError:
                If the `INDEX_CACHE_TTL_HOURS` variable is not an integer string.

        """
        ttl_str = os.getenv('INDEX_CACHE_TTL_HOURS', '4')

        try:
            ttl_hours = int(ttl_str)
        except ValueError as e:
            message = f'INDEX_CACHE_TTL_HOURS must be an integer, got: {ttl_str}'
            raise TypeError(message) from e

        return cls(index_file=service_dir / 'dbx_index.json', ttl_hours=ttl_hours)


@dataclass(slots=True, frozen=True)
class Config:
    """Root configuration with all nested scopes.

    Attributes:
        smtp: SMTP configuration for email notifications.
        dropbox: Dropbox API configuration.
        paths: File storage paths.
        email_state: Email state tracking configuration.
        cache: Cache configuration.

    """

    smtp: SMTPConfig
    dropbox: DropboxConfig
    paths: PathsConfig
    email_state: EmailStateConfig
    cache: CacheConfig

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        """Load complete configuration from environment variables.

        Args:
            env_file: Optional path to .env file. If None, uses default .env in cwd.

        Raises:
            ValueError: If any required configuration is missing or invalid.

        """
        if not load_dotenv(env_file):
            message = f"Failed to load environment variables from '{env_file or '.env'}'"
            raise ValueError(message)

        # Load nested configs
        config_dict: dict[str, Any] = {
            'dropbox': DropboxConfig.from_env(),
            'smtp': (smtp := SMTPConfig.from_env()),
            'paths': (paths := PathsConfig.from_env()),
            'cache': (cache := CacheConfig.from_env(paths.service_dir)),
            'email_state': EmailStateConfig.from_env(paths.service_dir),
        }

        console.bind(
            smtp_server=smtp.server,
            service_dir=str(paths.service_dir),
            cache_ttl_hours=cache.ttl_hours,
        ).info('Configuration loaded')

        return cls(**config_dict)
