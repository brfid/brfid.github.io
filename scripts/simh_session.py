"""Shared utilities for pexpect-driven SIMH console sessions.

Both vax_pexpect.py (Stage B) and pdp11_pexpect.py (Stage A) use the
same low-level patterns for logging, UUE validation, and batched heredoc
injection. This module centralises those to avoid drift between scripts.

Intentionally kept minimal: machine-specific boot sequences and file
capture logic remain in each stage's own script.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pexpect

# Delay between individual heredoc lines sent to the guest tty.
# 5 ms is long enough to prevent PTY input buffer overrun on SIMH.
LINE_DELAY: float = 0.005

# Lines per heredoc batch for UUE injection.
# Large batches cause PTY echo to stall; 10 lines keeps each heredoc short.
UUE_CHUNK_SIZE: int = 10


def make_logger(prefix: str):
    """Return a logger function that prefixes messages with a timestamp.

    Args:
        prefix: Short label prepended to every log line, e.g. "vax_pexpect".

    Returns:
        A callable ``log(msg: str) -> None`` that writes to stderr.
    """
    def _log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        print(f"[{prefix}] {ts}  {msg}", file=sys.stderr, flush=True)

    return _log


def validate_uu_spool(text: str, label: str = "brad.1.uu") -> None:
    """Validate that UUE spool text has a well-formed begin/end structure.

    Does not decode content — only checks structural markers.  Call this
    before injecting a spool into a guest to catch corruption early (before
    spending 5+ minutes in emulation).

    Args:
        text: Full UUE spool text.
        label: Human-readable artifact name for error messages.

    Raises:
        ValueError: If the spool is empty, missing a begin header, missing
            an end marker, or has no data lines.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"{label}: spool is empty")
    if not lines[0].startswith("begin "):
        raise ValueError(
            f"{label}: missing 'begin' header (first line: {lines[0]!r})"
        )
    if lines[-1] != "end":
        raise ValueError(
            f"{label}: missing 'end' marker (last line: {lines[-1]!r})"
        )
    if len(lines) < 3:
        raise ValueError(f"{label}: spool has no data lines between begin/end")


def strip_console(raw: bytes) -> str:
    """Decode PTY bytes and strip control codes for human-readable log display.

    Preserves printable ASCII and newlines; removes ANSI escape sequences,
    carriage returns, null bytes, and other non-printable control characters.

    Args:
        raw: Raw bytes from a pexpect ``child.before`` capture.

    Returns:
        Clean, human-readable string suitable for embedding in a log file.
    """
    text = raw.decode("ascii", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip ANSI/VT escape sequences (cursor movement, color, erase, etc.)
    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)
    text = re.sub(r"\x1b[=>]", "", text)
    # Strip remaining control characters except \n and \t
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Collapse runs of blank lines to at most two
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def log_console_section(machine: str, section: str, content: str) -> None:
    """Append a console snippet to the SECTIONS_LOG file if configured.

    Reads the ``SECTIONS_LOG`` environment variable for the destination path.
    Does nothing if the variable is unset or empty — safe to call unconditionally.

    Args:
        machine: Short machine label, e.g. ``"vax"`` or ``"pdp11"``.
        section: Section identifier, e.g. ``"vax-boot"`` or ``"pdp11-nroff"``.
        content: Human-readable console text (already stripped of PTY codes).
    """
    sections_log = os.environ.get("SECTIONS_LOG", "")
    if not sections_log:
        return
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    entry = {"machine": machine, "section": section, "ts": ts, "content": content}
    with open(sections_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def inject_batched_heredoc(
    child: "pexpect.spawn",
    remote_path: str,
    lines: list[str],
    prompt: str,
    timeout: float,
) -> None:
    """Write text lines to a remote guest file via batched heredocs.

    Splits ``lines`` into chunks of ``UUE_CHUNK_SIZE``, sending each chunk
    as a separate ``cat >> file << 'HEREDOC_EOF'`` command.  The first chunk
    uses ``>`` (create/truncate); subsequent chunks use ``>>`` (append).

    This pattern avoids PTY echo stall that occurs with a single large heredoc.
    Each line is sent with a ``LINE_DELAY`` pause to prevent tty buffer overrun.

    Args:
        child: Active pexpect.spawn session.
        remote_path: Destination path on the guest filesystem.
        lines: Text lines to write (must all be ≤62 chars for UUE content).
        prompt: Shell prompt pattern to expect after each heredoc batch.
        timeout: Timeout in seconds for each batch's expect() call.
    """
    for batch_idx, batch_start in enumerate(range(0, len(lines), UUE_CHUNK_SIZE)):
        batch = lines[batch_start : batch_start + UUE_CHUNK_SIZE]
        redirect = ">" if batch_idx == 0 else ">>"
        child.sendline(f"cat {redirect} {remote_path} << 'HEREDOC_EOF'")
        for line in batch:
            child.sendline(line)
            if LINE_DELAY:
                time.sleep(LINE_DELAY)
        child.sendline("HEREDOC_EOF")
        child.expect(prompt, timeout=timeout)
