from __future__ import annotations

from typing import Any

from arpanet_logging.collectors.imp import IMPCollector
from arpanet_logging.collectors.vax import VAXCollector
from arpanet_logging.parsers.arpanet import ArpanetParser
from arpanet_logging.parsers.bsd import BSDParser


class _FakeParser:
    def __init__(self, parsed: dict[str, Any], tags: list[str], level: str) -> None:
        self._parsed = parsed
        self._tags = tags
        self._level = level
        self.calls: list[tuple[str, str]] = []

    def parse(self, message: str) -> dict[str, Any]:
        self.calls.append(("parse", message))
        return self._parsed

    def extract_tags(self, message: str) -> list[str]:
        self.calls.append(("extract_tags", message))
        return self._tags

    def detect_log_level(self, message: str) -> str:
        self.calls.append(("detect_log_level", message))
        return self._level


def test_vax_collector_uses_default_parser_when_none_supplied() -> None:
    collector = VAXCollector(build_id="b1", container_name="arpanet-vax", storage=object())
    assert isinstance(collector.parser, BSDParser)


def test_imp_collector_uses_default_parser_when_none_supplied() -> None:
    collector = IMPCollector(build_id="b1", container_name="arpanet-imp1", storage=object())
    assert isinstance(collector.parser, ArpanetParser)


def test_vax_collector_parse_line_maps_parser_outputs_to_log_entry() -> None:
    parser = _FakeParser(parsed={"event": "boot"}, tags=["boot", "simh"], level="DEBUG")
    collector = VAXCollector(
        build_id="build-123",
        container_name="arpanet-vax",
        storage=object(),
        phase="phase2",
        parser=parser,
    )

    entry = collector.parse_line("2026-02-08T10:00:00Z", "VAX boot message")
    assert entry is not None
    assert entry.build_id == "build-123"
    assert entry.component == "vax"
    assert entry.phase == "phase2"
    assert entry.source == "console"
    assert entry.log_level == "DEBUG"
    assert entry.tags == ["boot", "simh"]
    assert entry.parsed == {"event": "boot"}
    assert [name for name, _ in parser.calls] == ["parse", "extract_tags", "detect_log_level"]


def test_imp_collector_parse_line_maps_parser_outputs_to_log_entry() -> None:
    parser = _FakeParser(parsed={"event": "route"}, tags=["routing"], level="INFO")
    collector = IMPCollector(
        build_id="build-456",
        container_name="arpanet-imp1",
        storage=object(),
        phase="phase3",
        parser=parser,
    )

    entry = collector.parse_line("2026-02-08T10:01:00Z", "IMP routing update")
    assert entry is not None
    assert entry.build_id == "build-456"
    assert entry.component == "imp"
    assert entry.phase == "phase3"
    assert entry.source == "console"
    assert entry.log_level == "INFO"
    assert entry.tags == ["routing"]
    assert entry.parsed == {"event": "route"}
    assert [name for name, _ in parser.calls] == ["parse", "extract_tags", "detect_log_level"]
