"""Shared logging, command, and transfer utilities for SIMH sessions."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pexpect

# Protect the guest tty from a host-speed heredoc stream.
LINE_DELAY: float = 0.005

# Larger heredocs can stall while the guest echoes their input.
HEREDOC_CHUNK_SIZE: int = 10

_COMMAND_STATUS_PATTERN = rb"__VINTAGE_RC_([0-9]+)__"


class GuestCommandError(RuntimeError):
    """Raised when a command inside a vintage guest returns nonzero."""


def make_logger(prefix: str) -> Callable[[str], None]:
    """Return a timestamped stderr logger with the given prefix."""

    def _log(msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        print(f"[{prefix}] {ts}  {msg}", file=sys.stderr, flush=True)

    return _log


def validate_uu_spool(text: str, label: str = "brad.bio.uu") -> None:
    """Require `begin`, an intervening encoded line, and a final `end` line."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"{label}: spool is empty")
    if not lines[0].startswith("begin "):
        raise ValueError(f"{label}: missing 'begin' header (first line: {lines[0]!r})")
    if lines[-1] != "end":
        raise ValueError(f"{label}: missing 'end' marker (last line: {lines[-1]!r})")
    if len(lines) < 3:
        raise ValueError(f"{label}: spool has no data lines between begin/end")


def strip_console(raw: bytes) -> str:
    """Decode ASCII with replacement and remove selected terminal controls."""
    text = raw.decode("ascii", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove ANSI and VT escape sequences.
    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)
    text = re.sub(r"\x1b[=>]", "", text)
    # Retain newlines and tabs while removing other control characters.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def run_checked(
    child: pexpect.spawn,
    command: str,
    prompt: str,
    timeout: float,
    *,
    label: str | None = None,
) -> bytes:
    """Run one guest-shell command and require an explicit zero exit status.

    Waiting for a prompt proves only that the shell is responsive. The command
    is followed by an exit-status marker whose literal form is split by shell
    quoting, so the tty's echoed command line cannot satisfy the marker match.
    This uses only Bourne-shell syntax supported by both historical guests.

    Args:
        child: Active pexpect session in bytes mode.
        command: Bourne-shell command to execute inside the guest.
        prompt: Distinctive shell prompt expected after the status marker.
        timeout: Timeout in seconds for the command and following prompt.
        label: Optional short operation name for failures.

    Returns:
        Console bytes emitted before the status marker.

    Raises:
        GuestCommandError: If the guest command returns nonzero or the marker
            does not contain a numeric status.
        pexpect.TIMEOUT: If the status marker or prompt does not arrive in time.
        pexpect.EOF: If SIMH exits while the command is running.
    """
    wrapped = f'{command}; vintage_rc=$?; echo __VINTAGE_RC_"${{vintage_rc}}__"'
    child.sendline(wrapped)
    child.expect(_COMMAND_STATUS_PATTERN, timeout=timeout)
    output = child.before or b""
    match = child.match
    try:
        status = int(match.group(1))
    except (AttributeError, TypeError, ValueError) as exc:
        raise GuestCommandError(f"{label or command}: guest returned an invalid status marker") from exc
    child.expect(prompt, timeout=timeout)
    if status != 0:
        detail = strip_console(output)[-500:]
        suffix = f": {detail}" if detail else ""
        raise GuestCommandError(f"{label or command}: guest exit status {status}{suffix}")
    return output


def log_console_section(machine: str, section: str, content: str) -> None:
    """Append one JSON Lines console record when SECTIONS_LOG is set."""
    sections_log = os.environ.get("SECTIONS_LOG", "")
    if not sections_log:
        return
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    entry = {"machine": machine, "section": section, "ts": ts, "content": content}
    with open(sections_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def inject_batched_heredoc(
    child: pexpect.spawn,
    remote_path: str,
    lines: list[str],
    prompt: str,
    timeout: float,
) -> None:
    """Write short text lines through throttled, fixed-size guest heredocs."""
    for batch_idx, batch_start in enumerate(range(0, len(lines), HEREDOC_CHUNK_SIZE)):
        batch = lines[batch_start : batch_start + HEREDOC_CHUNK_SIZE]
        redirect = ">" if batch_idx == 0 else ">>"
        child.sendline(f"cat {redirect} {remote_path} << 'HEREDOC_EOF'")
        for line in batch:
            child.sendline(line)
            if LINE_DELAY:
                time.sleep(LINE_DELAY)
        child.sendline("HEREDOC_EOF")
        child.expect(prompt, timeout=timeout)
    if lines:
        run_checked(
            child,
            f"test -s {shlex.quote(remote_path)}",
            prompt,
            timeout,
            label=f"write {remote_path}",
        )
