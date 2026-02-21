from __future__ import annotations

from host_logging.parsers.arpanet import ArpanetParser


def test_arpanet_parser_extracts_structured_fields_from_rich_line() -> None:
    parser = ArpanetParser()
    message = (
        "H316 simulator HI1: packet send type 002000 host 1 imp 2 "
        "link 3 route to imp2 connection established attach -u hi1 2000:172.20.0.10:2000 "
        "UDP port 2000 Good Registers 1822"
    )

    parsed = parser.parse(message)
    assert parsed is not None
    assert parsed["interface"] == "HI1"
    assert parsed["interface_type"] == "host"
    assert parsed["message_type"] == "002000"
    assert parsed["message_type_name"] == "Control message (IMP-to-host)"
    assert parsed["host_number"] == 1
    assert parsed["imp_number"] == 2
    assert parsed["link_number"] == 3
    assert parsed["routing_action"] == "route"
    assert parsed["routing_target"] == "imp2"
    assert parsed["connection_state"] == "established"
    assert parsed["local_port"] == 2000
    assert parsed["remote_host"] == "172.20.0.10"
    assert parsed["remote_port"] == 2000
    assert parsed["udp_port"] == 2000
    assert parsed["register_status"] == "Good"


def test_arpanet_parser_returns_none_for_non_matching_line() -> None:
    parser = ArpanetParser()
    assert parser.parse("completely unrelated simulator noise") is None


def test_arpanet_parser_extract_tags_covers_protocol_routing_udp_and_errors() -> None:
    parser = ArpanetParser()
    message = "HI1 send packet type=002000 route forward attach UDP 1822 bad fail"

    tags = parser.extract_tags(message)
    assert "host-interface" in tags
    assert "send" in tags
    assert "packet" in tags
    assert "protocol" in tags
    assert "routing" in tags
    assert "attach" in tags
    assert "udp" in tags
    assert "arpanet-1822" in tags
    assert "error" in tags


def test_arpanet_detect_log_level_precedence_error_over_warning_and_debug() -> None:
    parser = ArpanetParser()
    level = parser.detect_log_level("packet send timeout but also bad registers")
    assert level == "ERROR"
