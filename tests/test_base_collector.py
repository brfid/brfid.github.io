from __future__ import annotations

from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

from arpanet_logging.core.collector import BaseCollector
from arpanet_logging.core.models import LogEntry


class _FakeStorage:
    def __init__(self) -> None:
        self.raw: list[tuple[str, str]] = []
        self.events: list[LogEntry] = []

    def write_raw(self, component: str, message: str) -> None:
        self.raw.append((component, message))

    def write_event(self, entry: LogEntry) -> None:
        self.events.append(entry)


class _FakeParser:
    """Fake parser for testing default parse_line implementation."""
    def parse(self, message: str) -> dict[str, Any]:
        return {"len": len(message)}

    def extract_tags(self, message: str) -> list[str]:
        return ["parsed"]

    def detect_log_level(self, message: str) -> str:
        return "INFO"


class _TestCollector(BaseCollector):
    component_name = "test"
    log_source = "console"

    def __init__(self, storage: _FakeStorage, produce_entry: bool = True) -> None:
        # Use a fake parser that will be used by the default parse_line implementation
        parser = _FakeParser() if produce_entry else None
        super().__init__(
            build_id="build-test",
            container_name="arpanet-test",
            storage=storage,  # type: ignore[arg-type]
            phase="phase2",
            parser=parser,
        )
        # If produce_entry is False, override parse_line to return None
        if not produce_entry:
            self._return_none = True
        else:
            self._return_none = False

    def parse_line(self, timestamp: str, message: str) -> LogEntry | None:
        if self._return_none:
            return None
        # Use the default implementation from BaseCollector
        return super().parse_line(timestamp, message)


@pytest.fixture
def mock_docker(monkeypatch: MonkeyPatch) -> None:
    """Mock Docker client to avoid connection attempts in unit tests."""
    monkeypatch.setattr("arpanet_logging.core.collector.docker", None)


def test_process_line_splits_timestamp_and_writes_raw_and_event(mock_docker: None) -> None:
    storage = _FakeStorage()
    collector = _TestCollector(storage=storage, produce_entry=True)

    collector._process_line("2026-02-08T10:00:00Z hello world")

    assert storage.raw == [("test", "hello world")]
    assert len(storage.events) == 1
    event = storage.events[0]
    assert event.timestamp == "2026-02-08T10:00:00Z"
    assert event.message == "hello world"
    assert event.tags == ["parsed"]


def test_process_line_without_space_uses_fallback_timestamp(mock_docker: None) -> None:
    storage = _FakeStorage()
    collector = _TestCollector(storage=storage, produce_entry=True)

    collector._process_line("bareline")

    assert storage.raw == [("test", "bareline")]
    assert len(storage.events) == 1
    assert storage.events[0].timestamp.endswith("Z")


def test_process_line_skips_event_write_when_parse_returns_none(mock_docker: None) -> None:
    storage = _FakeStorage()
    collector = _TestCollector(storage=storage, produce_entry=False)

    collector._process_line("2026-02-08T10:00:00Z no structured event")

    assert storage.raw == [("test", "no structured event")]
    assert storage.events == []
