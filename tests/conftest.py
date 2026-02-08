from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply default test markers by directory.

    Marker policy:
    - tests/integration/** -> integration
    - tests/system/** -> docker + slow
    - everything else -> unit
    """
    for item in items:
        path = Path(str(item.fspath)).as_posix()

        if "/tests/system/" in path:
            item.add_marker(pytest.mark.docker)
            item.add_marker(pytest.mark.slow)
            continue

        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
            continue

        item.add_marker(pytest.mark.unit)
