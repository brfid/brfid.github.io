#!/usr/bin/env python3
"""Stage B: Compile and run bradman.c on VAX 4.3BSD using pexpect.

Spawns SIMH vax780 in stdin/stdout mode (no telnet port), boots 4.3BSD,
injects bradman.c and bio.vintage.yaml via heredoc, compiles with cc, runs
bradman to produce brad.bio.roff (troff source for the bio), uuencodes it on
the VAX, and captures brad.bio.uu (the UUCP spool file).

The VAX uuencodes brad.bio.roff itself before the host captures it — the host
acts as a UUCP store-and-forward node, routing brad.bio.uu to the PDP-11, which
runs nroff to fill and justify the bio into plain text.

Usage (inside Docker container built from Dockerfile.vax-pexpect):
    python3 /opt/vax_pexpect.py \
        --bradman  /build/bradman.c \
        --bio-yaml /build/bio.vintage.yaml \
        --output   /build/brad.bio.uu

Usage (direct, with SIMH vax780 + disk image available):
    python3 scripts/vax_pexpect.py \
        --bradman  vintage/machines/vax/bradman.c \
        --bio-yaml build/vintage/bio.vintage.yaml \
        --output   build/vintage/brad.bio.uu \
        --ini      /path/to/vax780-pexpect.ini \
        --workdir  /path/to/vax/working/dir

Exit codes:
    0  success — brad.bio.uu written
    1  failure — see stderr for details
"""

import argparse
import binascii
import sys
import time
from pathlib import Path

import pexpect
from simh_session import (
    inject_batched_heredoc,
    log_console_section,
    make_logger,
    strip_console,
    validate_uu_spool,
)

# Shell prompt injected after login — distinctive to avoid false matches.
_PROMPT = "VAXsh> "

_BOOT_TIMEOUT = 180  # 4.3BSD on VAX boots in ~60-90 s under SIMH
_LOGIN_TIMEOUT = 60  # after boot, login prompt appears within ~30 s
_CMD_TIMEOUT = 60
_COMPILE_TIMEOUT = 180  # cc on 4.3BSD VAX takes ~30-90 s for bradman.c
_UUE_TIMEOUT = 180  # UUE heredoc + cat can take longer on slow VAX emulation

# Paths written by Dockerfile.vax-pexpect at build time.
_PEXPECT_INI_CACHE = "/opt/vax-pexpect-ini-path.txt"
_VAX_BIN_CACHE = "/opt/vax-bin-path.txt"

_log = make_logger("vax_pexpect")


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Stage B: compile bradman.c on 4.3BSD VAX → brad.bio.roff")
    p.add_argument(
        "--bradman",
        default="/build/bradman.c",
        help="Path to bradman.c source (default: /build/bradman.c)",
    )
    p.add_argument(
        "--bio-yaml",
        default="/build/bio.vintage.yaml",
        help="Path to bio.vintage.yaml (default: /build/bio.vintage.yaml)",
    )
    p.add_argument(
        "--output",
        default="/build/brad.bio.uu",
        help="Path to write brad.bio.uu UUCP spool file (default: /build/brad.bio.uu)",
    )
    p.add_argument(
        "--ini",
        default=None,
        help=(f"SIMH VAX ini file. If not given, reads from {_PEXPECT_INI_CACHE} (written by Dockerfile.vax-pexpect)."),
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
    boot_rom = child.before or b""

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
    post_login = child.before or b""

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

    log_console_section("vax", "vax-boot", strip_console(boot_rom + b"\n" + post_login))


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
        time.sleep(0.005)
    child.sendline("HEREDOC_EOF")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log(f"Injected {remote_path}")


def _inject_file_uue(child: pexpect.spawn, remote_path: str, content: bytes) -> None:
    """Inject content via uuencode to bypass the 4.3BSD 256-byte tty line limit.

    UUE-encoded lines are always ≤62 characters. The encoded payload is
    injected into a temp .uu file via batched heredoc (via simh_session),
    then uudecode recreates the original file at remote_path.
    """
    name = Path(remote_path).name
    parent = str(Path(remote_path).parent)

    # Build UUE lines using binascii (not deprecated, unlike the uu module).
    # binascii.b2a_uu encodes 45 bytes per line → ≤62-char UUE lines.
    uue_lines = [f"begin 644 {name}"]
    for i in range(0, len(content), 45):
        uue_lines.append(binascii.b2a_uu(content[i : i + 45]).decode("ascii").rstrip("\n"))
    uue_lines += ["`", "end"]

    tmp_uu = f"/tmp/{name}.uu"
    _log(f"UUE-injecting {len(uue_lines)} encoded lines ({len(content)} bytes) → {remote_path}")

    inject_batched_heredoc(child, tmp_uu, uue_lines, _PROMPT, _UUE_TIMEOUT)

    # Decode: uudecode writes <name> into the current directory.
    child.sendline(f"cd {parent} && uudecode {tmp_uu} && rm {tmp_uu}")
    child.expect(_PROMPT, timeout=_UUE_TIMEOUT)
    _log(f"UUE-decoded: {remote_path}")


def _compile_and_run(child: pexpect.spawn) -> None:
    """Compile bradman.c with cc and run it to produce brad.bio.roff, then spool it."""
    _log("Compiling: cc -O -o bradman /tmp/bradman.c")
    child.sendline("cd /tmp && cc -O -o bradman bradman.c")
    # Compilation takes ~30-90 s on emulated 4.3BSD VAX.
    child.expect(_PROMPT, timeout=_COMPILE_TIMEOUT)
    _log("Compilation complete")
    compile_out = child.before or b""

    # Verify the binary was produced.
    child.sendline("ls -l /tmp/bradman")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    ls_bradman = child.before or b""

    log_console_section("vax", "vax-compile", strip_console(compile_out + b"\n" + ls_bradman))

    _log("Running: ./bradman -i bio.vintage.yaml -o brad.bio.roff")
    child.sendline("./bradman -i bio.vintage.yaml -o brad.bio.roff")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log("bradman run complete")
    bradman_out = child.before or b""

    # Verify output was produced.
    child.sendline("ls -l /tmp/brad.bio.roff")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    ls_roff = child.before or b""

    # Uuencode brad.bio.roff on the VAX — the VAX prepares its own outgoing UUCP spool.
    _log("Uuencoding: uuencode /tmp/brad.bio.roff brad.bio.roff > /tmp/brad.bio.uu")
    child.sendline("uuencode /tmp/brad.bio.roff brad.bio.roff > /tmp/brad.bio.uu")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log("[uucp] brad.bio.roff spooled on VAX as brad.bio.uu")
    uu_out = child.before or b""

    log_console_section("vax", "vax-run", strip_console(bradman_out + b"\n" + ls_roff + b"\n" + uu_out))


def _capture_spool(child: pexpect.spawn) -> str:
    """Cat /tmp/brad.bio.uu to the terminal and capture it between markers.

    brad.bio.uu is the UUCP spool file — uuencoded by the VAX itself.
    UUE content is guaranteed printable ASCII with lines ≤62 chars, so
    there is no risk of marker strings appearing in the content.

    Tty echo is disabled before sending the capture command so pexpect
    sees only actual shell output, not the echoed command line.
    """
    _log("[uucp] Capturing /tmp/brad.bio.uu from VAX spool…")
    child.sendline("stty -echo")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    child.sendline("echo '__BRADBIOUU_BEGIN__'; cat /tmp/brad.bio.uu; echo '__BRADBIOUU_END__'; stty echo")
    child.expect("__BRADBIOUU_BEGIN__", timeout=_CMD_TIMEOUT)
    child.expect("__BRADBIOUU_END__", timeout=_CMD_TIMEOUT)
    raw_bytes: bytes = child.before  # type: ignore[assignment]
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    raw = raw_bytes.decode("ascii", errors="replace")
    return raw.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n")


def main(argv=None) -> int:
    """Run Stage B and write the VAX-generated bio UUCP spool to disk.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code (``0`` on success, ``1`` on failure).
    """
    args = _parse_args(argv)

    # Validate inputs.
    bradman_path = Path(args.bradman)
    bio_yaml_path = Path(args.bio_yaml)
    for p in (bradman_path, bio_yaml_path):
        if not p.exists():
            _log(f"ERROR: input file not found: {p}")
            return 1

    bradman_c = bradman_path.read_text(encoding="ascii")
    # bio.vintage.yaml is ASCII-only by construction (vintage_yaml.py guarantees it).
    bio_yaml = bio_yaml_path.read_text(encoding="ascii")
    _log(f"bradman.c: {len(bradman_c.splitlines())} lines")
    _log(f"bio.vintage.yaml: {len(bio_yaml.splitlines())} lines")

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
        # Use UUE injection for YAML: the bioProfile summary can exceed the
        # 4.3BSD 256-byte tty canonical input buffer on a single line.
        _inject_file_uue(child, "/tmp/bio.vintage.yaml", bio_yaml.encode("ascii"))
        _compile_and_run(child)
        brad_bio_uu = _capture_spool(child)
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
        _log("Last SIMH output:")
        if child.before:
            _log(child.before.decode("ascii", errors="replace")[-500:])
        return 1
    finally:
        if child.isalive():
            child.terminate(force=True)

    try:
        validate_uu_spool(brad_bio_uu)
    except ValueError as exc:
        _log(f"ERROR: UUE validation failed: {exc}")
        _log("First 20 lines of captured spool:")
        for ln in brad_bio_uu.splitlines()[:20]:
            _log(f"  {ln!r}")
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(brad_bio_uu, encoding="ascii")
    _log(f"[uucp] Wrote spool: {args.output} ({len(brad_bio_uu.splitlines())} lines)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
