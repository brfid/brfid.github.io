from __future__ import annotations

import pytest

from arpanet.scripts.hi1_shim import (
    HEADER_SIZE,
    MAGIC,
    wrap_h316,
    unwrap_h316,
)


def test_wrap_h316_encodes_magic_sequence_and_word_count() -> None:
    payload = b"\x01\x02\x03"  # odd length to force padding
    packet = wrap_h316(payload, sequence=7)

    assert len(packet) == HEADER_SIZE + 4  # padded to 2 words
    assert int.from_bytes(packet[0:4], "big") == MAGIC
    assert int.from_bytes(packet[4:8], "big") == 7
    assert int.from_bytes(packet[8:10], "big") == 2
    assert packet[10:] == b"\x01\x02\x03\x00"


def test_unwrap_h316_round_trip_even_payload() -> None:
    payload = b"\xde\xad\xbe\xef"
    packet = wrap_h316(payload, sequence=123)
    assert unwrap_h316(packet) == payload


def test_unwrap_h316_rejects_bad_magic() -> None:
    packet = b"\x00\x00\x00\x00" + b"\x00\x00\x00\x01" + b"\x00\x01" + b"\xaa\xbb"
    with pytest.raises(ValueError, match="bad magic"):
        unwrap_h316(packet)


def test_unwrap_h316_rejects_truncated_payload() -> None:
    # Claims 2 words but only provides 1.
    packet = MAGIC.to_bytes(4, "big") + b"\x00\x00\x00\x01" + b"\x00\x02" + b"\xaa\xbb"
    with pytest.raises(ValueError, match="truncated payload"):
        unwrap_h316(packet)
