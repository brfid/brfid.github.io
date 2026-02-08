from __future__ import annotations

from typing import Any

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


class _TestCollector(BaseCollector):
    component_name = "test"
    log_source = "console"

    def __init__(self, storage: _FakeStorage, produce_entry: bool = True) -> None:
        super().__init__(
            build_id="build-test",
            container_name="arpanet-test",
            storage=storage,  # type: ignore[arg-type]
            phase="phase2",
            parser=None,
        )
        self.produce_entry = produce_entry

    def parse_line(self, timestamp: str, message: str) -> LogEntry | None:
        if not self.produce_entry:
            return None
        return self.create_entry(
            timestamp=timestamp,
            message=message,
            log_level="INFO",
            tags=["parsed"],
            parsed={"len": len(message)},
        )


def test_process_line_splits_timestamp_and_writes_raw_and_event() -> None:
    storage = _FakeStorage()
    collector = _TestCollector(storage=storage, produce_entry=True)

    collector._process_line("2026-02-08T10:00:00Z hello world")

    assert storage.raw == [("test", "hello world")]
    assert len(storage.events) == 1
    event = storage.events[0]
    assert event.timestamp == "2026-02-08T10:00:00Z"
    assert event.message == "hello world"
    assert event.tags == ["parsed"]


def test_process_line_without_space_uses_fallback_timestamp() -> None:
    storage = _FakeStorage()
    collector = _TestCollector(storage=storage, produce_entry=True)

    collector._process_line("bareline")

    assert storage.raw == [("test", "bareline")]
    assert len(storage.events) == 1
    assert storage.events[0].timestamp.endswith("Z")


def test_process_line_skips_event_write_when_parse_returns_none() -> None:
    storage = _FakeStorage()
    collector = _TestCollector(storage=storage, produce_entry=False)

    collector._process_line("2026-02-08T10:00:00Z no structured event")

    assert storage.raw == [("test", "no structured event")]
    assert storage.events == []
