from __future__ import annotations

from resume_generator.uudecode import (
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
