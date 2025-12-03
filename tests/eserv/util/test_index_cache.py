"""Test suite for util/index_cache.py Dropbox folder index caching."""

from __future__ import annotations

import shutil
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from rampy import test

from eserv.util.index_cache import IndexCache

if TYPE_CHECKING:
    from typing import Any, Final

SAMPLE_INDEX: Final[dict[str, dict[str, str]]] = {
    '/Client Files/Smith v. Jones': {'id': '123', 'name': 'Smith v. Jones'},
    '/Client Files/Doe Corporation': {'id': '456', 'name': 'Doe Corporation'},
}
EXPECT_SIZE: Final[int] = len(SAMPLE_INDEX)


def scenario(
    *,
    ttl_hours: int = 4,
    test_staleness: bool = False,
    test_persistence: bool = False,
) -> dict[str, Any]:
    """Create test scenario for IndexCache."""
    return {
        'params': [ttl_hours, SAMPLE_INDEX],
        'test_staleness': test_staleness,
        'test_persistence': test_persistence,
    }


@test.scenarios(**{
    'refresh and staleness': scenario(),
    'staleness after ttl': scenario(test_staleness=True),
    'persistence': scenario(test_persistence=True),
})
class TestIndexCache:
    def test(
        self,
        /,
        params: list[Any],
        test_staleness: bool,
        test_persistence: bool,
    ):
        temp_dir = Path(tempfile.mkdtemp())
        try:
            ttl_hours, sample_index = params
            cache_file = temp_dir / 'dbx_index.json'

            if test_persistence:
                # Test persistence across instances
                cache1 = IndexCache(cache_file=cache_file, ttl_hours=ttl_hours)
                cache1.refresh(sample_index)

                cache2 = IndexCache(cache_file=cache_file, ttl_hours=ttl_hours)
                loaded = cache2.get_index()
                assert len(loaded) == len(sample_index)
                assert '/Client Files/Smith v. Jones' in loaded

            elif test_staleness:
                # Test TTL expiration
                cache = IndexCache(cache_file=cache_file, ttl_hours=ttl_hours)
                cache.refresh(sample_index)
                assert not cache.is_stale()

                # Simulate old data
                cache._prev_refresh = datetime.now(UTC) - timedelta(hours=ttl_hours + 1)
                assert cache.is_stale()

            else:
                # Test basic refresh and retrieval
                cache = IndexCache(cache_file=cache_file, ttl_hours=ttl_hours)
                assert cache.is_stale()  # Initially stale

                cache.refresh(sample_index)
                assert not cache.is_stale()

                # Test retrieval
                cached = cache.get_index()
                assert len(cached) == EXPECT_SIZE

                # Test find_folder
                folder = cache.find_folder('/Client Files/Smith v. Jones')
                assert folder is not None
                assert folder['name'] == 'Smith v. Jones'

                # Test get_all_paths
                paths = cache.get_all_paths()
                assert len(paths) == EXPECT_SIZE

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
