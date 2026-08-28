#!/usr/bin/env python3
"""Run stage A on PDP-11 2.11BSD and write the nroff-rendered bio."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from collections.abc import Sequence
from pathlib import Path

import pexpect
from simh_session import (
    GuestCommandError,
    inject_batched_heredoc,
    log_console_section,
    make_logger,
    run_checked,
    strip_console,
    validate_uu_spool,
)

# VAX and PDP-11 boot, shell, and shutdown state machines stay separate even
# where their host-side error handling looks alike.
# pylint: disable=duplicate-code

# Lowercase prompt letters keep the prompt outside the UUE alphabet.
_PROMPT = "PDPsh> "
_CAPTURE_BEGIN = re.compile(rb"(?m)^__BRAD_BIO_TXT_BEGIN__\r?$")
_CAPTURE_END = re.compile(rb"(?m)^__BRAD_BIO_TXT_END__\r?$")

_BOOT_TIMEOUT = 300  # Allow for CPU contention on shared hosted runners.
_CMD_TIMEOUT = 60
_NROFF_TIMEOUT = 600  # nroff on PDP-11 can take 5+ min on emulated hardware
_UUE_TIMEOUT = 120  # per-batch UUE heredoc + cat timeout

_log = make_logger("pdp11_pexpect")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage A: render brad.bio.roff → brad.bio.txt via nroff on 2.11BSD")
    p.add_argument(
        "--input",
        required=True,
        help="Path to brad.bio.uu UUCP spool file (uuencoded by the VAX)",
    )
    p.add_argument("--output", required=True, help="Path to write brad.bio.txt")
    p.add_argument(
        "--ini",
        default="/opt/pdp11/pdp11-pexpect.ini",
        help="SIMH PDP-11 ini file (default: /opt/pdp11/pdp11-pexpect.ini)",
    )
    p.add_argument(
        "--workdir",
        default="/opt/pdp11",
        help="Working directory for SIMH (must contain disk image; default: /opt/pdp11)",
    )
    p.add_argument(
        "--simh-bin",
        default="pdp11",
        help="SIMH PDP-11 binary name or path (default: pdp11)",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Echo all SIMH/BSD console output to stderr",
    )
    return p.parse_args(argv)


def _boot(child: pexpect.spawn) -> None:
    """Boot 2.11BSD to a root shell with /usr mounted, then set a custom prompt."""
    # Disk revisions use either a CR-prefixed colon prompt or "Boot:".
    _log("Waiting for 2.11BSD boot prompt (\\r: or Boot:)…")
    child.expect(["\r: ", "Boot:"], timeout=_BOOT_TIMEOUT)
    _log("Got boot prompt; pressing Enter to boot unix kernel")
    boot_pre = child.before or b""
    child.sendline("")

    _log("Waiting for root # prompt (this can take up to 5 minutes)…")
    child.expect(["# ", "\\$ "], timeout=_BOOT_TIMEOUT)
    _log("Reached root shell")
    kernel_boot = child.before or b""

    # csh does not support this PS1 assignment and treats quoted heredoc
    # delimiters literally. Switch shells before setting the prompt or sending files.
    child.sendline("exec /bin/sh")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("Switched to /bin/sh")

    # The default ERASE (#) and KILL (@) bytes occur in UUE data.
    # Send literal DEL and Ctrl-U bytes before the first file transfer.
    child.sendline("stty erase \x7f kill \x15")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("stty: ERASE → DEL, KILL → Ctrl-U (safe for heredoc injection)")

    child.sendline("PS1='" + _PROMPT + "'")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log(f"Custom prompt set: {_PROMPT!r}")

    mount_out = run_checked(
        child,
        "mount /usr && test -f /usr/bin/nroff && test -f /usr/bin/uudecode",
        _PROMPT,
        _CMD_TIMEOUT,
        label="mount /usr",
    )
    _log("/usr mounted; nroff and uudecode are available")

    log_console_section("pdp11", "pdp11-boot", strip_console(boot_pre + b"\n" + kernel_boot + b"\n" + mount_out))


def _deliver_uu_spool(child: pexpect.spawn, uu_text: str, remote_uu_path: str) -> None:
    """Write the VAX-generated UUE spool and decode its troff payload."""
    uue_lines = uu_text.splitlines()
    parent = str(Path(remote_uu_path).parent)

    _log(f"[uucp] Delivering spool {remote_uu_path} ({len(uue_lines)} encoded lines) to PDP-11…")

    inject_batched_heredoc(child, remote_uu_path, uue_lines, _PROMPT, _UUE_TIMEOUT)

    decoded_name = "brad.bio.roff"
    run_checked(
        child,
        (
            f"cd {shlex.quote(parent)} && rm -f {decoded_name} && uudecode {shlex.quote(remote_uu_path)} "
            f"&& test -s {decoded_name} && rm {shlex.quote(remote_uu_path)}"
        ),
        _PROMPT,
        _UUE_TIMEOUT,
        label="decode brad.bio.uu",
    )
    _log(f"[uucp] Spool delivered and decoded: brad.bio.roff at {parent}/brad.bio.roff")


def _run_nroff(child: pexpect.spawn) -> str:
    """Render base troff requests and capture the output between marker lines."""
    # Line-printer mode removes terminal controls; /dev/null prevents page prompts.
    _log("Running: nroff -Tlp /tmp/brad.bio.roff < /dev/null > /tmp/brad.bio.txt")
    nroff_out = run_checked(
        child,
        "rm -f /tmp/brad.bio.txt && nroff -Tlp /tmp/brad.bio.roff < /dev/null > /tmp/brad.bio.txt "
        "&& test -s /tmp/brad.bio.txt && ls -l /tmp/brad.bio.txt",
        _PROMPT,
        _NROFF_TIMEOUT,
        label="render brad.bio.roff",
    )
    _log("nroff complete")
    log_console_section("pdp11", "pdp11-nroff", strip_console(nroff_out))

    # Disable echo before sending the marker command to prevent pexpect
    # from matching markers in the command echo rather than actual output.
    _log("Capturing /tmp/brad.bio.txt via markers…")
    child.sendline("stty -echo")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    child.sendline("echo '__BRAD_BIO_TXT_BEGIN__'; cat /tmp/brad.bio.txt; echo '__BRAD_BIO_TXT_END__'; stty echo")
    child.expect(_CAPTURE_BEGIN, timeout=_CMD_TIMEOUT)
    child.expect(_CAPTURE_END, timeout=_CMD_TIMEOUT)
    raw_bytes: bytes = child.before
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    raw = raw_bytes.decode("ascii", errors="replace")
    return raw


def _clean_nroff_output(raw: str) -> str:
    r"""Normalize captured nroff text and remove terminal formatting artifacts."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = text.lstrip("\n")

    # Remove the character before each backspace and retain its overstrike.
    text = re.sub(r".\x08", "", text)
    text = text.replace("\f", "\n")
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:  # pylint: disable=too-many-return-statements
    """Run stage A and return its process exit code."""
    args = _parse_args(argv)

    brad_bio_uu_path = Path(args.input)
    if not brad_bio_uu_path.exists():
        _log(f"ERROR: input file not found: {args.input}")
        return 1

    brad_bio_uu = brad_bio_uu_path.read_text(encoding="ascii")
    _log(f"[uucp] Spool received: {args.input} ({len(brad_bio_uu.splitlines())} encoded lines)")

    try:
        validate_uu_spool(brad_bio_uu)
    except ValueError as exc:
        _log(f"ERROR: UUE framing check failed before SIMH launch: {exc}")
        _log("First 10 lines of spool:")
        for ln in brad_bio_uu.splitlines()[:10]:
            _log(f"  {ln!r}")
        return 1
    _log("[uucp] Spool structure validated (begin/end markers present)")

    ini = args.ini
    workdir = args.workdir
    _log(f"Spawning: {args.simh_bin} {ini}  (cwd={workdir})")

    child = pexpect.spawn(
        args.simh_bin,
        [ini],
        cwd=workdir,
        timeout=_BOOT_TIMEOUT,
        encoding=None,
    )

    if args.verbose:
        child.logfile_read = sys.stderr.buffer

    try:
        _boot(child)
        _deliver_uu_spool(child, brad_bio_uu, "/tmp/brad.bio.uu")
        raw = _run_nroff(child)
        child.sendline("exit")
        # 2.11BSD can restart login after shell exit instead of returning EOF.
        try:
            child.expect(pexpect.EOF, timeout=30)
        except pexpect.TIMEOUT:
            _log("Note: SIMH did not exit cleanly within 30s; will force-terminate")
    except pexpect.TIMEOUT as exc:
        _log(f"TIMEOUT: {exc}")
        _log("Last SIMH output:")
        if child.before:
            _log(child.before.decode("ascii", errors="replace")[-500:])
        return 1
    except pexpect.EOF:
        _log("SIMH process exited unexpectedly")
        return 1
    except GuestCommandError as exc:
        _log(f"GUEST COMMAND FAILED: {exc}")
        return 1
    finally:
        if child.isalive():
            child.terminate(force=True)

    output = _clean_nroff_output(raw)

    if not output.strip():
        _log("ERROR: nroff output is empty after cleaning; check brad.bio.roff input")
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    _log(f"Wrote: {args.output} ({len(output.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
