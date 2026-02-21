from __future__ import annotations

import pytest

from resume_generator.uudecode import (
    _decode_uu_line,
    decode_marked_uuencode,
    decode_uuencode_block,
    extract_marked_region,
)
from tests.helpers import uuencode_bytes


def test_extract_marked_region() -> None:
    text = "aaa\n<<<BEGIN>>>\nhello\n<<<END>>>\nbbb\n"
    extracted = extract_marked_region(text, begin_marker="<<<BEGIN>>>", end_marker="<<<END>>>")
    assert extracted == "hello\n"


def test_decode_uuencode_block_roundtrip() -> None:
    payload = b"hello\nworld\n" * 10
    block = uuencode_bytes(payload, filename="file.txt")
    res = decode_uuencode_block(block)
    assert res.filename == "file.txt"
    assert res.data == payload


def test_decode_marked_uuencode_ignores_noise() -> None:
    payload = b"brad.1 contents"
    block = uuencode_bytes(payload, filename="brad.1")
    transcript = "\n".join(
        [
            "booting...",
            "<<<BRAD_1_UU_BEGIN>>>",
            "noise line we should ignore",
            block.rstrip("\n"),
            "<<<BRAD_1_UU_END>>>",
            "done",
        ]
    )
    res = decode_marked_uuencode(
        transcript,
        begin_marker="<<<BRAD_1_UU_BEGIN>>>",
        end_marker="<<<BRAD_1_UU_END>>>",
    )
    assert res.filename == "brad.1"
    assert res.data == payload


def test_decode_uuencode_trims_trailing_garbage() -> None:
    payload = b"hello world" * 5
    block = uuencode_bytes(payload, filename="payload.bin")
    lines = block.splitlines()
    begin_index = next(i for i, line in enumerate(lines) if line.startswith("begin "))
    data_index = begin_index + 1
    lines[data_index] = lines[data_index] + "EXTRA"
    res = decode_uuencode_block("\n".join(lines) + "\n")
    assert res.filename == "payload.bin"
    assert res.data == payload


def test_extract_marked_region_requires_markers() -> None:
    text = "no markers here\n"

    with pytest.raises(ValueError, match="Missing begin marker"):
        extract_marked_region(text, begin_marker="<<<BEGIN>>>", end_marker="<<<END>>>")


def test_extract_marked_region_requires_begin_newline() -> None:
    text = "<<<BEGIN>>>"

    with pytest.raises(ValueError, match="must end with a newline"):
        extract_marked_region(text, begin_marker="<<<BEGIN>>>", end_marker="<<<END>>>")


def test_decode_uuencode_block_requires_begin_and_end_lines() -> None:
    with pytest.raises(ValueError, match="Missing uuencode begin line"):
        decode_uuencode_block("not a uu block")

    with pytest.raises(ValueError, match="Missing uuencode end line"):
        decode_uuencode_block("begin 644 x.bin\n#0V%T\n")


def test_decode_uuencode_block_rejects_invalid_header() -> None:
    with pytest.raises(ValueError, match="Invalid uuencode begin line"):
        decode_uuencode_block("begin 644\n`\nend\n")


def test_decode_uuencode_block_tolerates_malformed_data_line() -> None:
    block = "\n".join(
        [
            "begin 644 bad.bin",
            "#$$$",  # malformed line; decoder should remain tolerant
            "end",
            "",
        ]
    )
    res = decode_uuencode_block(block)
    assert res.filename == "bad.bin"
    assert isinstance(res.data, bytes)


def test_decode_uu_line_handles_empty_and_zero_length() -> None:
    assert _decode_uu_line("") == b""
    assert _decode_uu_line("`") == b""


def test_decode_uu_line_decodes_partial_groups_consistently() -> None:
    payload = b"abcde"
    block = uuencode_bytes(payload, filename="x.bin")
    data_line = block.splitlines()[1]
    # Ensure low-level decoder matches expected bytes for a normal uu line.
    assert _decode_uu_line(data_line) == payload

    # Truncate encoded payload mid-group; decoder should return only safe decoded prefix.
    truncated = data_line[:-1]
    decoded = _decode_uu_line(truncated)
    assert decoded in (payload, payload[:-1], payload[:-2])
