"""Test suite for util/config.py configuration management."""

from __future__ import annotations

from typing import Final

import eserv

MIN_TOKEN_LENGTH: Final[int] = 10


def test_config_from_env():
    """Test Config.from_env() loads all configuration."""
    config = eserv.config()

    # Verify SMTP config
    assert config.smtp.server
    assert config.smtp.port > 0
    assert '@' in config.smtp.from_addr
    assert '@' in config.smtp.to_addr

    # Verify Dropbox config
    assert (dropbox_token := config.credentials['dropbox'].access_token)
    assert len(dropbox_token) > MIN_TOKEN_LENGTH

    # Verify Outlook config
    assert (outlook_token := config.credentials['microsoft-outlook'].access_token)
    assert len(outlook_token) > MIN_TOKEN_LENGTH

    # Verify paths config
    assert config.paths.service_dir.exists()
    assert config.paths.manual_review_folder

    # Verify cache config
    assert config.cache.ttl_hours > 0
    assert config.cache.index_file.parent == config.paths.service_dir

    # Verify email state config
    assert config.state.state_file.parent == config.paths.service_dir
