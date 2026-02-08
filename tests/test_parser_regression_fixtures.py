from __future__ import annotations

from pathlib import Path

from arpanet_logging.parsers.arpanet import ArpanetParser
from arpanet_logging.parsers.bsd import BSDParser


FIXTURES = Path("tests/fixtures")


def _load_lines(name: str) -> list[str]:
    data = (FIXTURES / name).read_text(encoding="utf-8")
    return [line for line in data.splitlines() if line.strip()]


def test_arpanet_fixture_lines_have_stable_parse_expectations() -> None:
    parser = ArpanetParser()
    lines = _load_lines("arpanet_lines.txt")

    parsed_1 = parser.parse(lines[0])
    assert parsed_1 is not None
    assert parsed_1["interface"] == "HI1"
    assert parsed_1["interface_type"] == "host"
    assert parsed_1["message_type"] == "002000"
    assert parsed_1["connection_state"] == "established"

    parsed_2 = parser.parse(lines[1])
    assert parsed_2 is not None
    assert parsed_2["interface"] == "MI1"
    assert parsed_2["interface_type"] == "modem"
    assert parsed_2["message_type"] == "005000"
    assert parsed_2["connection_state"] == "closed"

    assert parser.parse(lines[2]) is None

    assert parser.detect_log_level(lines[3]) == "WARNING"
    assert parser.detect_log_level(lines[4]) == "ERROR"


def test_bsd_fixture_lines_have_stable_parse_expectations() -> None:
    parser = BSDParser()
    lines = _load_lines("bsd_lines.txt")

    parsed_attach = parser.parse(lines[0])
    assert parsed_attach is not None
    assert parsed_attach["event_type"] == "interface_attach"
    assert parsed_attach["interface"] == "de0"

    parsed_hw = parser.parse(lines[1])
    assert parsed_hw is not None
    assert parsed_hw["event_type"] == "hw_address"
    assert parsed_hw["mac_address"] == "08:00:2b:92:49:19"

    parsed_flags = parser.parse(lines[2])
    assert parsed_flags is not None
    assert parsed_flags["event_type"] == "interface_flags"
    assert "RUNNING" in parsed_flags["flags"]

    parsed_inet = parser.parse(lines[3])
    assert parsed_inet is not None
    assert parsed_inet["event_type"] == "inet"
    assert parsed_inet["ip_address"] == "172.20.0.10"

    parsed_version = parser.parse(lines[4])
    assert parsed_version is not None
    assert parsed_version["event_type"] == "bsd_version"
    assert parsed_version["version"] == "4.3"

    parsed_daemons = parser.parse(lines[5])
    assert parsed_daemons is not None
    assert parsed_daemons["event_type"] == "daemons"
    assert parsed_daemons["daemons"] == ["rwhod", "inetd", "printer"]

    parsed_login = parser.parse(lines[6])
    assert parsed_login is not None
    assert parsed_login["event_type"] == "login"
    assert parsed_login["username"] == "root"

    parsed_simh = parser.parse(lines[7])
    assert parsed_simh is not None
    assert parsed_simh["event_type"] == "simh_connected"

    assert parser.detect_log_level(lines[8]) == "ERROR"
    assert parser.parse(lines[9]) is None
