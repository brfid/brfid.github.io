from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark tests under tests/integration and treat all others as unit tests."""
    for item in items:
        path = Path(str(item.fspath)).as_posix()

        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
            continue

        item.add_marker(pytest.mark.unit)
