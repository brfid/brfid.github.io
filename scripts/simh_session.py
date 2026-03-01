"""Shared utilities for pexpect-driven SIMH console sessions.

Both vax_pexpect.py (Stage B) and pdp11_pexpect.py (Stage A) use the
same low-level patterns for logging, UUE validation, and batched heredoc
injection. This module centralises those to avoid drift between scripts.

Intentionally kept minimal: machine-specific boot sequences and file
capture logic remain in each stage's own script.
"""

from __future__ import annotations

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
