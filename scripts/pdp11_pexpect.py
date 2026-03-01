#!/usr/bin/env python3
"""Stage A: Render brad.1 via nroff -man on PDP-11 2.11BSD using pexpect.

Spawns SIMH pdp11 in stdin/stdout mode (no telnet port), boots 2.11BSD,
receives brad.1.uu (the UUCP spool file produced by the VAX), injects it
via heredoc, uudecodes it to brad.1, runs nroff -man, captures output.

The host acts as a UUCP store-and-forward node: brad.1.uu arrives from the
VAX spool and is delivered here for decoding and rendering.

Usage (inside Docker container):
    python3 pdp11_pexpect.py --input /build/brad.1.uu --output /build/brad.man.txt

Usage (direct, if SIMH + disk image are available locally):
    python3 pdp11_pexpect.py \
        --input build/vintage/brad.1.uu \
        --output build/vintage/brad.man.txt \
        --ini vintage/machines/pdp11/configs/pdp11-pexpect.ini \
        --workdir /opt/pdp11

Exit codes:
    0  success — brad.man.txt written
    1  failure — see stderr for details
"""

import argparse
import re
import sys
import time
from pathlib import Path

import pexpect

# Shell prompt injected after boot; distinctive enough to avoid false matches
# in heredoc echo output. Uses '>' not '#' so it can't conflict with content.
_PROMPT = "PDPsh> "

_BOOT_TIMEOUT = 180    # 2.11BSD on PDP-11 boots slowly (~90-120s under SIMH)
_CMD_TIMEOUT = 60
_NROFF_TIMEOUT = 600   # nroff on PDP-11 can take 5+ min on emulated hardware
_UUE_TIMEOUT = 120     # per-batch UUE heredoc + cat timeout
_LINE_DELAY = 0.005    # 5 ms between heredoc lines; prevents tty buffer overrun


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    print(f"[pdp11_pexpect] {ts}  {msg}", file=sys.stderr, flush=True)


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Stage A: render brad.1 → brad.man.txt via nroff on 2.11BSD"
    )
    p.add_argument("--input", required=True, help="Path to brad.1.uu UUCP spool file (uuencoded by the VAX)")
    p.add_argument("--output", required=True, help="Path to write brad.man.txt")
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
    # 2.11BSD's 2-stage boot shows: "73Boot from xp(0,0,0) at 0176700\n\r: "
    # The actual prompt is "\r: " (CR + colon + space), not "Boot:".
    # Accept both patterns to handle variation across SIMH/disk-image versions.
    _log("Waiting for 2.11BSD boot prompt (\\r: or Boot:)…")
    child.expect(["\r: ", "Boot:"], timeout=_BOOT_TIMEOUT)
    _log("Got boot prompt — pressing Enter to boot unix kernel")
    child.sendline("")

    # 2.11BSD on PDP-11 under SIMH takes ~60-120 s to reach root shell.
    _log("Waiting for root # prompt (this takes up to 2 minutes)…")
    child.expect(["# ", "\\$ "], timeout=_BOOT_TIMEOUT)
    _log("Reached root shell")

    # 2.11BSD root's login shell may be /bin/csh.  csh has the same two
    # incompatibilities as 4.3BSD VAX: PS1= is ignored and heredoc
    # `<< 'DELIM'` treats the quoted string as the terminator (not DELIM).
    # Switch to /bin/sh before any prompt or heredoc work.
    child.sendline("exec /bin/sh")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("Switched to /bin/sh")

    # 2.11BSD default tty ERASE is '#' (0x23) and KILL is '@' (0x40).
    # Both fall in the UUE character range and corrupt heredoc injection if
    # brad.1 contains either char (e.g., '@' in email addresses).
    # Move both out of the UUE range: DEL (0x7F) and Ctrl-U (0x15).
    child.sendline("stty erase \x7f kill \x15")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("stty: ERASE → DEL, KILL → Ctrl-U (safe for heredoc injection)")

    child.sendline("mount /usr")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("/usr mounted — nroff and uudecode now available")

    # Switch to a distinctive prompt to avoid false matches on '#' in file content.
    child.sendline("PS1='" + _PROMPT + "'")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log(f"Custom prompt set: {_PROMPT!r}")


def _deliver_uu_spool(child: pexpect.spawn, uu_text: str, remote_uu_path: str) -> None:
    """Deliver a UUCP spool file (brad.1.uu) to the PDP-11 guest and decode it.

    The spool file was uuencoded by the VAX; the host routed it here.
    UUE lines are guaranteed ≤62 chars — no CANBSIZ overflow risk.
    Inject in batches of 10 lines to avoid PTY echo stall.
    2.11BSD uudecode writes the decoded file into the current directory.
    """
    uue_lines = uu_text.splitlines()
    parent = str(Path(remote_uu_path).parent)

    _log(
        f"[uucp] Delivering spool {remote_uu_path} "
        f"({len(uue_lines)} encoded lines) to PDP-11…"
    )

    _UUE_CHUNK_SIZE = 10
    for batch_idx, batch_start in enumerate(
        range(0, len(uue_lines), _UUE_CHUNK_SIZE)
    ):
        batch = uue_lines[batch_start : batch_start + _UUE_CHUNK_SIZE]
        redirect = ">" if batch_idx == 0 else ">>"
        child.sendline(f"cat {redirect} {remote_uu_path} << 'HEREDOC_EOF'")
        for line in batch:
            child.sendline(line)
            if _LINE_DELAY:
                time.sleep(_LINE_DELAY)
        child.sendline("HEREDOC_EOF")
        child.expect(_PROMPT, timeout=_UUE_TIMEOUT)

    child.sendline(f"cd {parent} && uudecode {remote_uu_path} && rm {remote_uu_path}")
    child.expect(_PROMPT, timeout=_UUE_TIMEOUT)
    _log(f"[uucp] Spool delivered and decoded: brad.1 at {parent}/brad.1")


def _run_nroff(child: pexpect.spawn) -> str:
    """Run nroff -man on /tmp/brad.1 and return the rendered text.

    Output is captured between unique markers to isolate it from terminal echo.
    """
    # -Tlp: line printer mode — no terminal-specific control sequences.
    # < /dev/null: prevents nroff from pausing at page breaks waiting for
    #   keypress on stdin (old nroff behaviour when stderr is a tty).
    _log("Running: nroff -man -Tlp /tmp/brad.1 < /dev/null > /tmp/brad.man.txt")
    child.sendline("nroff -man -Tlp /tmp/brad.1 < /dev/null > /tmp/brad.man.txt")
    child.expect(_PROMPT, timeout=_NROFF_TIMEOUT)
    _log("nroff complete")

    # Verify the output file was produced.
    child.sendline("ls -l /tmp/brad.man.txt")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    # Disable echo before sending the marker command to prevent pexpect
    # from matching markers in the command echo rather than actual output.
    _log("Capturing /tmp/brad.man.txt via markers…")
    child.sendline("stty -echo")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    child.sendline(
        "echo '__BRAD_MAN_TXT_BEGIN__'; cat /tmp/brad.man.txt; "
        "echo '__BRAD_MAN_TXT_END__'; stty echo"
    )
    child.expect("__BRAD_MAN_TXT_BEGIN__", timeout=_CMD_TIMEOUT)
    child.expect("__BRAD_MAN_TXT_END__", timeout=_CMD_TIMEOUT)
    raw_bytes: bytes = child.before  # type: ignore[assignment]
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    raw = raw_bytes.decode("ascii", errors="replace")
    return raw


def _clean_nroff_output(raw: str) -> str:
    """Clean terminal and SIMH artefacts from captured nroff output.

    Steps:
    1. Normalize line endings (pty adds \\r before \\n).
    2. Strip leading newline that follows the __BRAD_MAN_TXT_BEGIN__ marker.
    3. Strip backspace-overstrike sequences (nroff bold/underline on vintage tty).
    4. Strip form feeds (nroff page breaks).
    5. Strip trailing whitespace from each line.
    """
    # 1. Normalize CRLF → LF
    text = raw.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Strip leading newline(s) (artefact of marker capture boundary)
    text = text.lstrip("\n")

    # 3. Remove backspace-overstrike: any char followed by \b is overstriking;
    #    keep the character after the \b (or just drop the pair for simplicity).
    text = re.sub(r".\x08", "", text)

    # 4. Strip form feeds
    text = text.replace("\f", "\n")

    # 5. Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]

    # 6. Drop leading/trailing blank lines from the document
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    args = _parse_args(argv)

    brad1_uu_path = Path(args.input)
    if not brad1_uu_path.exists():
        _log(f"ERROR: input file not found: {args.input}")
        return 1

    brad1_uu = brad1_uu_path.read_text(encoding="ascii")
    _log(f"[uucp] Spool received: {args.input} ({len(brad1_uu.splitlines())} encoded lines)")

    ini = args.ini
    workdir = args.workdir
    cmd = f"{args.simh_bin} {ini}"
    _log(f"Spawning: {cmd}  (cwd={workdir})")

    child = pexpect.spawn(
        cmd,
        cwd=workdir,
        timeout=_BOOT_TIMEOUT,
        encoding=None,  # bytes mode — decode manually for safety
    )

    if args.verbose:
        child.logfile_read = sys.stderr.buffer

    try:
        _boot(child)
        _deliver_uu_spool(child, brad1_uu, "/tmp/brad.1.uu")
        raw = _run_nroff(child)
        child.sendline("exit")
        # 2.11BSD may restart getty/login after shell exits rather than
        # handing EOF back to SIMH. finally block force-terminates anyway.
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
    finally:
        if child.isalive():
            child.terminate(force=True)

    output = _clean_nroff_output(raw)

    if not output.strip():
        _log("ERROR: nroff output is empty after cleaning — check brad.1 input")
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    _log(f"Wrote: {args.output} ({len(output.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
