"""Extract and decode uuencoded blocks from a console transcript."""

from __future__ import annotations

import binascii
from dataclasses import dataclass


@dataclass(frozen=True)
class UuDecodeResult:
    """Decoded data plus metadata from a uuencode block."""

    filename: str
    data: bytes


def _decode_uu_line(line: str) -> bytes:
    """Decode a single uuencode data line (tolerant fallback).

    Args:
        line: A uuencoded data line.

    Returns:
        The decoded bytes for the line.
    """
    if not line:
        return b""
    length = (ord(line[0]) - 0x20) & 0x3F
    if length == 0:
        return b""
    out = bytearray()
    for i in range(1, len(line), 4):
        chunk = line[i : i + 4]
        if len(chunk) < 4:
            break
        vals = [((ord(ch) - 0x20) & 0x3F) for ch in chunk]
        out.append((vals[0] << 2) | (vals[1] >> 4))
        out.append(((vals[1] & 0x0F) << 4) | (vals[2] >> 2))
        out.append(((vals[2] & 0x03) << 6) | vals[3])
    return bytes(out[:length])


def extract_marked_region(text: str, *, begin_marker: str, end_marker: str) -> str:
    """Extract text between hard markers.

    Args:
        text: Full transcript text.
        begin_marker: Marker line indicating region start.
        end_marker: Marker line indicating region end.

    Returns:
        The substring between markers (exclusive).

    Raises:
        ValueError: If markers are missing or out of order.
    """
    begin_idx = text.find(begin_marker)
    if begin_idx < 0:
        raise ValueError(f"Missing begin marker: {begin_marker!r}")
    begin_end = text.find("\n", begin_idx)
    if begin_end < 0:
        raise ValueError("Begin marker must end with a newline")

    end_idx = text.find(end_marker, begin_end + 1)
    if end_idx < 0:
        raise ValueError(f"Missing end marker: {end_marker!r}")
    if end_idx <= begin_end:
        raise ValueError("End marker appears before begin marker")

    return text[begin_end + 1 : end_idx]


def decode_uuencode_block(block_text: str) -> UuDecodeResult:  # pylint: disable=too-many-branches
    """Decode a uuencode block into bytes.

    Args:
        block_text: Text containing an embedded uuencode block. This may contain
            surrounding noise; only the first `begin ...` to `end` is decoded.

    Returns:
        Decoded bytes plus filename from the uuencode header.

    Raises:
        ValueError: If the block cannot be parsed or decoded.
    """
    lines = [line.rstrip("\r") for line in block_text.splitlines()]

    begin_line_index = -1
    for i, line in enumerate(lines):
        if line.startswith("begin "):
            begin_line_index = i
            break
    if begin_line_index < 0:
        raise ValueError("Missing uuencode begin line")

    header = lines[begin_line_index].split(maxsplit=2)
    if len(header) != 3:
        raise ValueError(f"Invalid uuencode begin line: {lines[begin_line_index]!r}")
    filename = header[2].strip()
    if not filename:
        raise ValueError("uuencode header missing filename")

    decoded: bytearray = bytearray()
    found_end = False
    for line in lines[begin_line_index + 1 :]:
        if line == "end":
            found_end = True
            break
        if not line:
            continue
        # Some terminals may append extra characters; trim to the expected uu line length.
        try:
            uu_len = (ord(line[0]) - 0x20) & 0x3F
            expected_len = 1 + ((uu_len + 2) // 3) * 4
            if 1 < expected_len < len(line):
                line = line[:expected_len]
        except (IndexError, TypeError, ValueError):
            pass  # Keep line as-is if length calculation fails
        try:
            decoded.extend(binascii.a2b_uu(line.encode("ascii")))
        except (binascii.Error, UnicodeEncodeError):
            try:
                decoded.extend(_decode_uu_line(line))
            except Exception as exc:
                raise ValueError(f"Invalid uuencoded line: {line!r}") from exc

    if not found_end:
        raise ValueError("Missing uuencode end line")

    return UuDecodeResult(filename=filename, data=bytes(decoded))


def decode_marked_uuencode(
    transcript: str,
    *,
    begin_marker: str,
    end_marker: str,
) -> UuDecodeResult:
    """Extract a marked transcript region and decode its uuencode block."""
    region = extract_marked_region(transcript, begin_marker=begin_marker, end_marker=end_marker)
    return decode_uuencode_block(region)
