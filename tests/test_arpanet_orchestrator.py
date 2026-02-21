from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

import host_logging.orchestrator as orchestrator_module


@dataclass
class _FakeStats:
    total_lines: int = 0
    errors: int = 0
    warnings: int = 0
    tags: dict[str, int] | None = None


class _FakeStorage:
    def __init__(self, build_id: str, base_path: str) -> None:
        self.build_id = build_id
        self.base_path = base_path
        self.build_path = f"{base_path}/builds/{build_id}"
        self.initialized_metadata = None
        self.finalized_metadata = None

    def initialize(self, metadata: Any) -> None:
        self.initialized_metadata = metadata

    def finalize(self, metadata: Any) -> None:
        self.finalized_metadata = metadata

    def list_components(self) -> list[str]:
        return []

    def get_stats(self, component: str) -> _FakeStats:
        return _FakeStats(tags={})


class _FakeCollector:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.component_name = kwargs["container_name"].replace("arpanet-", "")
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def test_orchestrator_start_creates_collectors_for_supported_components(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orchestrator_module, "LogStorage", _FakeStorage)
    monkeypatch.setattr(orchestrator_module, "COLLECTORS_AVAILABLE", True)

    # Mock get_collector_class to return fake collector
    def _mock_get_collector_class(component: str) -> type[_FakeCollector]:
        if component in ("vax", "imp1"):
            return _FakeCollector
        raise ValueError(f"No collector for {component}")

    monkeypatch.setattr(orchestrator_module, "get_collector_class", _mock_get_collector_class)
    monkeypatch.setattr(orchestrator_module.signal, "signal", lambda *_args, **_kwargs: None)

    orchestrator = orchestrator_module.LogOrchestrator(
        build_id="build-1",
        components=["vax", "imp1", "unknown"],
        phase="phase2",
        base_path="/tmp/logs",
    )

    orchestrator.start()

    assert isinstance(orchestrator.storage, _FakeStorage)
    assert orchestrator.storage.initialized_metadata is orchestrator.metadata
    assert len(orchestrator.collectors) == 2

    vax_collector, imp_collector = orchestrator.collectors
    assert vax_collector.started is True
    assert imp_collector.started is True
    assert vax_collector.kwargs["container_name"] == "arpanet-vax"
    assert imp_collector.kwargs["container_name"] == "arpanet-imp1"
    assert imp_collector.component_name == "imp1"


def test_orchestrator_stop_stops_collectors_and_finalizes_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orchestrator_module, "LogStorage", _FakeStorage)
    monkeypatch.setattr(orchestrator_module, "COLLECTORS_AVAILABLE", True)

    # Mock get_collector_class
    monkeypatch.setattr(orchestrator_module, "get_collector_class", lambda _c: _FakeCollector)
    monkeypatch.setattr(orchestrator_module.signal, "signal", lambda *_args, **_kwargs: None)

    orchestrator = orchestrator_module.LogOrchestrator(
        build_id="build-2",
        components=["vax", "imp1"],
        phase="phase2",
        base_path="/tmp/logs",
    )
    orchestrator.collectors = [_FakeCollector(container_name="arpanet-vax")]

    orchestrator.stop()

    collector = orchestrator.collectors[0]
    assert collector.stopped is True
    assert orchestrator.metadata.status == "success"
    assert orchestrator.metadata.end_time is not None
    assert isinstance(orchestrator.storage, _FakeStorage)
    assert orchestrator.storage.finalized_metadata is orchestrator.metadata


def test_orchestrator_signal_handler_stops_and_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(orchestrator_module, "LogStorage", _FakeStorage)
    monkeypatch.setattr(orchestrator_module.signal, "signal", lambda *_args, **_kwargs: None)

    orchestrator = orchestrator_module.LogOrchestrator(
        build_id="build-3",
        components=["vax"],
        phase="phase2",
        base_path="/tmp/logs",
    )

    stopped = SimpleNamespace(called=False)

    def _fake_stop() -> None:
        stopped.called = True

    monkeypatch.setattr(orchestrator, "stop", _fake_stop)

    with pytest.raises(SystemExit):
        orchestrator._signal_handler(15, None)

    assert stopped.called is True
