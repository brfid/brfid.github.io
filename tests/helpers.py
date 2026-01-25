from __future__ import annotations

import binascii
from pathlib import Path


def write_minimal_resume(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "basics:",
                "  name: Test User",
                "  label: Engineer",
                "  profiles:",
                "    - network: LinkedIn",
                "      url: https://linkedin.com/in/test",
                "work: []",
                "skills: []",
                "",
            ]
        ),
        encoding="utf-8",
    )


def uuencode_bytes(data: bytes, filename: str = "x.bin") -> str:
    lines = [f"begin 644 {filename}"]
    for i in range(0, len(data), 45):
        chunk = data[i : i + 45]
        lines.append(binascii.b2a_uu(chunk).decode("ascii").rstrip("\n"))
    lines.append("`")
    lines.append("end")
    return "\n".join(lines) + "\n"
