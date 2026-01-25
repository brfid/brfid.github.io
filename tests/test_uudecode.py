from __future__ import annotations

import binascii

from resume_generator.uudecode import (
    decode_marked_uuencode,
    decode_uuencode_block,
    extract_marked_region,
)


def _uuencode_bytes(data: bytes, filename: str = "x.bin") -> str:
    lines = [f"begin 644 {filename}"]
    for i in range(0, len(data), 45):
        chunk = data[i : i + 45]
        lines.append(binascii.b2a_uu(chunk).decode("ascii").rstrip("\n"))
    lines.append("`")  # zero-length terminator line
    lines.append("end")
    return "\n".join(lines) + "\n"


def test_extract_marked_region() -> None:
    text = "aaa\n<<<BEGIN>>>\nhello\n<<<END>>>\nbbb\n"
    extracted = extract_marked_region(text, begin_marker="<<<BEGIN>>>", end_marker="<<<END>>>")
    assert extracted == "hello\n"


def test_decode_uuencode_block_roundtrip() -> None:
    payload = b"hello\nworld\n" * 10
    block = _uuencode_bytes(payload, filename="file.txt")
    res = decode_uuencode_block(block)
    assert res.filename == "file.txt"
    assert res.data == payload


def test_decode_marked_uuencode_ignores_noise() -> None:
    payload = b"brad.1 contents"
    block = _uuencode_bytes(payload, filename="brad.1")
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
