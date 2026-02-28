#!/usr/bin/env python3
"""Stage B: Compile and run bradman.c on VAX 4.3BSD using pexpect.

Spawns SIMH vax780 in stdin/stdout mode (no telnet port), boots 4.3BSD,
injects bradman.c and resume.vintage.yaml via heredoc, compiles with cc,
runs bradman to produce brad.1 (troff source), captures brad.1.

Usage (inside Docker container built from Dockerfile.vax-pexpect):
    python3 /opt/vax_pexpect.py \
        --bradman   /build/bradman.c \
        --resume-yaml /build/resume.vintage.yaml \
        --output    /build/brad.1

Usage (direct, with SIMH vax780 + disk image available):
    python3 scripts/vax_pexpect.py \
        --bradman   vintage/machines/vax/bradman.c \
        --resume-yaml build/vintage/resume.vintage.yaml \
        --output    build/vintage/brad.1 \
        --ini       /path/to/vax780-pexpect.ini \
        --workdir   /path/to/vax/working/dir

Exit codes:
    0  success — brad.1 written
    1  failure — see stderr for details
"""

import argparse
import io
import sys
import time
import unicodedata
import uu
from pathlib import Path

import pexpect

# Common Unicode → ASCII substitutions for content fed to the ASCII-only VAX guest.
_UNICODE_SUBS: dict[str, str] = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quotation mark
    "\u2019": "'",    # right single quotation mark
    "\u201c": '"',    # left double quotation mark
    "\u201d": '"',    # right double quotation mark
    "\u2026": "...",  # horizontal ellipsis
    "\u00a0": " ",    # non-breaking space
    "\u2022": "*",    # bullet
}


def _to_ascii(text: str) -> str:
    """Transliterate common Unicode to ASCII for injection into the VAX guest.

    Applies a small substitution table for typographic characters, then uses
    NFKD normalization to decompose accented letters before stripping anything
    that still can't be represented in ASCII.
    """
    for ch, sub in _UNICODE_SUBS.items():
        text = text.replace(ch, sub)
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", errors="replace").decode("ascii")

# Shell prompt injected after login — distinctive to avoid false matches.
_PROMPT = "VAXsh> "

_BOOT_TIMEOUT = 180    # 4.3BSD on VAX boots in ~60-90 s under SIMH
_LOGIN_TIMEOUT = 60    # after boot, login prompt appears within ~30 s
_CMD_TIMEOUT = 60
_COMPILE_TIMEOUT = 180 # cc on 4.3BSD VAX takes ~30-90 s for bradman.c
_UUE_TIMEOUT = 180     # UUE heredoc + cat can take longer on slow VAX emulation
_LINE_DELAY = 0.005    # 5 ms between heredoc lines; prevents tty buffer overrun

# Paths written by Dockerfile.vax-pexpect at build time.
_PEXPECT_INI_CACHE = "/opt/vax-pexpect-ini-path.txt"
_VAX_BIN_CACHE = "/opt/vax-bin-path.txt"


def _log(msg: str) -> None:
    print(f"[vax_pexpect] {msg}", file=sys.stderr, flush=True)


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Stage B: compile bradman.c on 4.3BSD VAX → brad.1"
    )
    p.add_argument(
        "--bradman",
        default="/build/bradman.c",
        help="Path to bradman.c source (default: /build/bradman.c)",
    )
    p.add_argument(
        "--resume-yaml",
        default="/build/resume.vintage.yaml",
        help="Path to resume.vintage.yaml (default: /build/resume.vintage.yaml)",
    )
    p.add_argument(
        "--output",
        default="/build/brad.1",
        help="Path to write brad.1 roff output (default: /build/brad.1)",
    )
    p.add_argument(
        "--ini",
        default=None,
        help=(
            "SIMH VAX ini file. If not given, reads from "
            f"{_PEXPECT_INI_CACHE} (written by Dockerfile.vax-pexpect)."
        ),
    )
    p.add_argument(
        "--workdir",
        default=None,
        help="Working directory for SIMH (defaults to ini file's parent directory).",
    )
    p.add_argument(
        "--simh-bin",
        default=None,
        help=(
            "SIMH VAX binary name or path. If not given, reads from "
            f"{_VAX_BIN_CACHE} (written by Dockerfile.vax-pexpect), "
            "then falls back to 'vax780'."
        ),
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Echo all SIMH/BSD console output to stderr",
    )
    return p.parse_args(argv)


def _resolve_simh_config(args) -> tuple[str, str, str]:
    """Return (simh_bin, ini_path, workdir) from args or Docker build cache."""
    # SIMH binary
    simh_bin = args.simh_bin
    if not simh_bin:
        cache = Path(_VAX_BIN_CACHE)
        if cache.exists():
            simh_bin = cache.read_text().strip()
            _log(f"SIMH binary from cache: {simh_bin}")
        else:
            simh_bin = "vax780"
            _log(f"Using default SIMH binary: {simh_bin}")

    # INI path
    ini_path = args.ini
    if not ini_path:
        cache = Path(_PEXPECT_INI_CACHE)
        if cache.exists():
            ini_path = cache.read_text().strip()
            _log(f"INI path from cache: {ini_path}")
        else:
            _log(
                f"ERROR: --ini not given and {_PEXPECT_INI_CACHE} not found. "
                "Build the Docker image with Dockerfile.vax-pexpect, or pass --ini."
            )
            sys.exit(1)

    if not Path(ini_path).exists():
        _log(f"ERROR: INI file not found: {ini_path}")
        sys.exit(1)

    # Working directory (must contain disk image referenced by ini)
    workdir = args.workdir or str(Path(ini_path).parent)
    return simh_bin, ini_path, workdir


def _boot(child: pexpect.spawn) -> None:
    """Boot 4.3BSD to a root shell, then set a custom prompt."""
    _log("Waiting for 4.3BSD login: prompt…")
    # VAX SIMH emits boot ROM messages before the BSD login prompt.
    child.expect("login:", timeout=_BOOT_TIMEOUT)
    _log("Got login: prompt")

    child.sendline("root")
    # Use "# " (hash space) not "#" — the 4.3BSD kernel version string
    # (e.g. "BSD UNIX #10") contains "#" without a following space; the
    # actual root shell prompt is "# " or "hostname# ".
    idx = child.expect(["Password:", "# ", "\\$ "], timeout=_LOGIN_TIMEOUT)
    if idx == 0:
        _log("Password prompt received — sending empty password")
        child.sendline("")
        child.expect(["# ", "\\$ "], timeout=_LOGIN_TIMEOUT)

    _log("Logged in as root")

    # 4.3BSD root's default login shell is /bin/csh, not /bin/sh.  csh has
    # two incompatibilities that break the pipeline:
    #   1. PS1='...' is a Bourne sh idiom; csh ignores it and prints
    #      "PS1=...: Command not found." — pexpect appears to match
    #      VAXsh> in the error text rather than a real prompt.
    #   2. csh heredoc `<< 'HEREDOC_EOF'` uses the QUOTED string
    #      'HEREDOC_EOF' (including the single quotes) as the terminator.
    #      We send the unquoted HEREDOC_EOF — it never matches and the
    #      heredoc hangs indefinitely.
    # Switch to /bin/sh before any stty, prompt, or heredoc work.
    child.sendline("exec /bin/sh")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("Switched to /bin/sh (avoids csh heredoc quoting quirk)")

    # 4.3BSD's default ERASE character is '#' (0x23) and KILL is '@' (0x40).
    # Both fall in the UUE character range (0x20-0x60): each '#' in a UUE
    # heredoc erases the previous input character; each '@' kills the entire
    # input line. This silently corrupts UUE injection while bradman.c (which
    # contains no '#' or '@') works fine.
    #
    # Change ERASE to DEL (0x7F) and KILL to Ctrl-U (0x15) — both are outside
    # the UUE range. Send the actual bytes, not caret-notation strings, so the
    # 4.3BSD shell receives the single-character argument stty expects.
    child.sendline("stty erase \x7f kill \x15")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("stty: ERASE → DEL, KILL → Ctrl-U (safe for UUE injection)")

    # Set a distinctive prompt before injecting any file content.
    child.sendline("PS1='" + _PROMPT + "'")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log(f"Custom prompt set: {_PROMPT!r}")


def _inject_file(child: pexpect.spawn, remote_path: str, content: str) -> None:
    """Inject text content into a VAX guest file via quoted heredoc.

    Quoted delimiter suppresses all shell substitution, so '#include', '$',
    and backslashes in C source are passed through literally.

    Use only for content where all lines are ≤200 chars. The 4.3BSD tty
    canonical input buffer is 256 bytes; longer lines trigger BEL and get
    truncated. For long-line content use _inject_file_uue() instead.
    """
    lines = content.splitlines()
    _log(f"Injecting {len(lines)} lines → {remote_path}")
    child.sendline(f"cat > {remote_path} << 'HEREDOC_EOF'")
    for line in lines:
        child.sendline(line)
        if _LINE_DELAY:
            time.sleep(_LINE_DELAY)
    child.sendline("HEREDOC_EOF")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log(f"Injected {remote_path}")


def _inject_file_uue(child: pexpect.spawn, remote_path: str, content: bytes) -> None:
    """Inject content via uuencode to bypass the 4.3BSD 256-byte tty line limit.

    UUE-encoded lines are always ≤62 characters. The encoded payload is
    injected into a temp .uu file via heredoc, then uudecode recreates
    the original file at remote_path. 4.3BSD ships uudecode in /usr/bin.
    """
    name = Path(remote_path).name
    parent = str(Path(remote_path).parent)

    in_buf = io.BytesIO(content)
    out_buf = io.BytesIO()
    uu.encode(in_buf, out_buf, name, 0o644)
    uue_lines = out_buf.getvalue().decode("ascii").splitlines()

    tmp_uu = f"/tmp/{name}.uu"
    _log(
        f"UUE-injecting {len(uue_lines)} encoded lines "
        f"({len(content)} bytes) → {remote_path}"
    )

    # Inject in small batches to avoid the 4.3BSD tty echo stall.
    # A single heredoc with 90+ UUE lines causes the PTY echo to stall
    # indefinitely. Batches of _UUE_CHUNK_SIZE lines keep each heredoc
    # small enough to complete promptly.
    _UUE_CHUNK_SIZE = 10

    # First batch uses '>' (create/truncate); subsequent batches use '>>'.
    for batch_idx, batch_start in enumerate(
        range(0, len(uue_lines), _UUE_CHUNK_SIZE)
    ):
        batch = uue_lines[batch_start : batch_start + _UUE_CHUNK_SIZE]
        redirect = ">" if batch_idx == 0 else ">>"
        child.sendline(f"cat {redirect} {tmp_uu} << 'HEREDOC_EOF'")
        for line in batch:
            child.sendline(line)
            if _LINE_DELAY:
                time.sleep(_LINE_DELAY)
        child.sendline("HEREDOC_EOF")
        child.expect(_PROMPT, timeout=_UUE_TIMEOUT)

    # Decode: uudecode writes <name> into the current directory.
    child.sendline(f"cd {parent} && uudecode {tmp_uu} && rm {tmp_uu}")
    child.expect(_PROMPT, timeout=_UUE_TIMEOUT)
    _log(f"UUE-decoded: {remote_path}")


def _compile_and_run(child: pexpect.spawn) -> None:
    """Compile bradman.c with cc and run it to produce brad.1."""
    _log("Compiling: cc -O -o bradman /tmp/bradman.c")
    child.sendline("cd /tmp && cc -O -o bradman bradman.c")
    # Compilation takes ~30-90 s on emulated 4.3BSD VAX.
    child.expect(_PROMPT, timeout=_COMPILE_TIMEOUT)
    _log("Compilation complete")

    # Verify the binary was produced.
    child.sendline("ls -l /tmp/bradman")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    _log("Running: ./bradman -i resume.vintage.yaml -o brad.1")
    child.sendline("./bradman -i resume.vintage.yaml -o brad.1")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log("bradman run complete")

    # Verify output was produced.
    child.sendline("ls -l /tmp/brad.1")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)


def _capture_brad1(child: pexpect.spawn) -> str:
    """Cat /tmp/brad.1 to the terminal and capture it between markers."""
    _log("Capturing /tmp/brad.1 via markers…")
    child.sendline(
        "echo '__BRAD1_BEGIN__'; cat /tmp/brad.1; echo '__BRAD1_END__'"
    )
    child.expect("__BRAD1_BEGIN__", timeout=_CMD_TIMEOUT)
    child.expect("__BRAD1_END__", timeout=_CMD_TIMEOUT)
    raw_bytes: bytes = child.before  # type: ignore[assignment]
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    raw = raw_bytes.decode("ascii", errors="replace")
    # Normalize CRLF → LF, strip leading newline from marker boundary.
    text = raw.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n")
    return text


def main(argv=None) -> int:
    args = _parse_args(argv)

    # Validate inputs.
    bradman_path = Path(args.bradman)
    resume_yaml_path = Path(args.resume_yaml)
    for p in (bradman_path, resume_yaml_path):
        if not p.exists():
            _log(f"ERROR: input file not found: {p}")
            return 1

    bradman_c = bradman_path.read_text(encoding="ascii")
    resume_yaml = _to_ascii(resume_yaml_path.read_text(encoding="utf-8"))
    _log(f"bradman.c: {len(bradman_c.splitlines())} lines")
    _log(f"resume.vintage.yaml: {len(resume_yaml.splitlines())} lines")

    simh_bin, ini_path, workdir = _resolve_simh_config(args)
    cmd = f"{simh_bin} {ini_path}"
    _log(f"Spawning: {cmd}  (cwd={workdir})")

    child = pexpect.spawn(
        cmd,
        cwd=workdir,
        timeout=_BOOT_TIMEOUT,
        encoding=None,  # bytes mode — decode manually
    )

    if args.verbose:
        child.logfile_read = sys.stderr.buffer

    try:
        _boot(child)
        _inject_file(child, "/tmp/bradman.c", bradman_c)
        # Use UUE injection for YAML: resume.vintage.yaml has lines up to 500+
        # chars which overflow the 4.3BSD 256-byte tty canonical input buffer.
        _inject_file_uue(child, "/tmp/resume.vintage.yaml", resume_yaml.encode("ascii"))
        _compile_and_run(child)
        brad1_text = _capture_brad1(child)
        child.sendline("exit")
        # 4.3BSD may restart getty/login after the shell exits rather than
        # handing EOF back to SIMH immediately.  The finally block will
        # force-terminate SIMH regardless, so a timeout here is non-fatal.
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

    if not brad1_text.strip():
        _log("ERROR: brad.1 output is empty — check bradman.c and resume.vintage.yaml")
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(brad1_text, encoding="utf-8")
    _log(f"Wrote: {args.output} ({len(brad1_text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
