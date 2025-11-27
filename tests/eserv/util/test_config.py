"""Test suite for util/config.py configuration management."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rampy import test

from eserv.util.config import Config

if TYPE_CHECKING:
    from typing import Any


def scenario() -> dict[str, Any]:
    """Test Config.from_env() loads all configuration."""
    return {
        'params': [],
        'exception': None,
    }


@test.scenarios(**{
    'load config from env': scenario(),
})
class TestConfigFromEnv:
    def test(self, /, params: list[Any], exception: type[Exception] | None):
        def execute() -> None:
            config = Config.from_env()

            # Verify SMTP config
            assert config.smtp.server
            assert config.smtp.port > 0
            assert '@' in config.smtp.from_addr
            assert '@' in config.smtp.to_addr

            # Verify Dropbox config
            assert config.dropbox.token
            assert len(config.dropbox.token) > 10

            # Verify paths config
            assert config.paths.service_dir.exists()
            assert config.paths.manual_review_folder

            # Verify cache config
            assert config.cache.ttl_hours > 0
            assert config.cache.index_file.parent == config.paths.service_dir

            # Verify email state config
            assert config.email_state.state_file.parent == config.paths.service_dir

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()
