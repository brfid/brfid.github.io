#!/usr/bin/env python3
"""Run stage B on VAX 4.3BSD and write the generated UUCP spool."""

from __future__ import annotations

import argparse
import binascii
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

_PROMPT = "VAXsh> "
_CAPTURE_BEGIN = re.compile(rb"(?m)^__BRADBIOUU_BEGIN__\r?$")
_CAPTURE_END = re.compile(rb"(?m)^__BRADBIOUU_END__\r?$")

_BOOT_TIMEOUT = 180  # 4.3BSD on VAX boots in ~60-90 s under SIMH
_LOGIN_TIMEOUT = 60  # after boot, login prompt appears within ~30 s
_CMD_TIMEOUT = 60
_COMPILE_TIMEOUT = 180  # cc on 4.3BSD VAX takes ~30-90 s for bradman.c
_UUE_TIMEOUT = 180  # UUE heredoc + cat can take longer on slow VAX emulation

# Paths written by Dockerfile.vax-pexpect at build time.
_PEXPECT_INI_CACHE = "/opt/vax-pexpect-ini-path.txt"
_VAX_BIN_CACHE = "/opt/vax-bin-path.txt"

_log = make_logger("vax_pexpect")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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


def _resolve_simh_config(args: argparse.Namespace) -> tuple[str, str, str]:
    """Return (simh_bin, ini_path, workdir) from args or Docker build cache."""
    simh_bin = args.simh_bin
    if not simh_bin:
        cache = Path(_VAX_BIN_CACHE)
        if cache.exists():
            simh_bin = cache.read_text(encoding="ascii").strip()
            _log(f"SIMH binary from cache: {simh_bin}")
        else:
            simh_bin = "vax780"
            _log(f"Using default SIMH binary: {simh_bin}")

    ini_path = args.ini
    if not ini_path:
        cache = Path(_PEXPECT_INI_CACHE)
        if cache.exists():
            ini_path = cache.read_text(encoding="ascii").strip()
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

    workdir = args.workdir or str(Path(ini_path).parent)
    return simh_bin, ini_path, workdir


def _boot(child: pexpect.spawn) -> None:
    """Boot 4.3BSD to a root shell, then set a custom prompt."""
    _log("Waiting for 4.3BSD login: prompt…")
    child.expect("login:", timeout=_BOOT_TIMEOUT)
    _log("Got login: prompt")
    boot_rom = child.before or b""

    child.sendline("root")
    # A bare # also occurs in the kernel banner; the root prompt ends in "# ".
    idx = child.expect(["Password:", "# ", "\\$ "], timeout=_LOGIN_TIMEOUT)
    if idx == 0:
        _log("Password prompt received; sending an empty password")
        child.sendline("")
        child.expect(["# ", "\\$ "], timeout=_LOGIN_TIMEOUT)

    _log("Logged in as root")
    post_login = child.before or b""

    # csh does not support this PS1 assignment and treats a quoted heredoc
    # delimiter literally. Switch shells before setting the prompt or sending files.
    child.sendline("exec /bin/sh")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("Switched to /bin/sh (avoids csh heredoc quoting quirk)")

    # The default ERASE (#) and KILL (@) bytes occur in source and UUE data.
    # Send literal DEL and Ctrl-U bytes before the first file transfer.
    child.sendline("stty erase \x7f kill \x15")
    child.expect(["# ", "\\$ "], timeout=_CMD_TIMEOUT)
    _log("stty: ERASE → DEL, KILL → Ctrl-U (safe for UUE injection)")

    child.sendline("PS1='" + _PROMPT + "'")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    _log(f"Custom prompt set: {_PROMPT!r}")

    log_console_section("vax", "vax-boot", strip_console(boot_rom + b"\n" + post_login))


def _inject_file(child: pexpect.spawn, remote_path: str, content: str) -> None:
    """Write text lines of at most 200 characters through a quoted heredoc."""
    lines = content.splitlines()
    _log(f"Injecting {len(lines)} lines → {remote_path}")
    inject_batched_heredoc(child, remote_path, lines, _PROMPT, _CMD_TIMEOUT)
    _log(f"Injected {remote_path}")


def _inject_file_uue(child: pexpect.spawn, remote_path: str, content: bytes) -> None:
    """Write arbitrary content as short UUE lines, then decode it in the guest."""
    name = Path(remote_path).name
    parent = str(Path(remote_path).parent)

    # Encoding 45 bytes per line keeps every UUE line at or below 62 characters.
    uue_lines = [f"begin 644 {name}"]
    for i in range(0, len(content), 45):
        uue_lines.append(binascii.b2a_uu(content[i : i + 45]).decode("ascii").rstrip("\n"))
    uue_lines += ["`", "end"]

    tmp_uu = f"/tmp/{name}.uu"
    _log(f"UUE-injecting {len(uue_lines)} encoded lines ({len(content)} bytes) → {remote_path}")

    inject_batched_heredoc(child, tmp_uu, uue_lines, _PROMPT, _UUE_TIMEOUT)

    run_checked(
        child,
        (
            f"cd {shlex.quote(parent)} && rm -f {shlex.quote(name)} && "
            f"uudecode {shlex.quote(tmp_uu)} && test -s {shlex.quote(name)} && rm {shlex.quote(tmp_uu)}"
        ),
        _PROMPT,
        _UUE_TIMEOUT,
        label=f"decode {remote_path}",
    )
    _log(f"UUE-decoded: {remote_path}")


def _compile_and_run(child: pexpect.spawn) -> None:
    """Compile bradman.c with cc and run it to produce brad.bio.roff, then spool it."""
    _log("Compiling: cc -O -o bradman /tmp/bradman.c")
    compile_out = run_checked(
        child,
        "cd /tmp && rm -f bradman && cc -O -o bradman bradman.c && test -f bradman",
        _PROMPT,
        _COMPILE_TIMEOUT,
        label="compile bradman.c",
    )
    _log("Compilation complete")
    log_console_section("vax", "vax-compile", strip_console(compile_out))

    _log("Running: ./bradman -i bio.vintage.yaml -o brad.bio.roff")
    bradman_out = run_checked(
        child,
        "cd /tmp && rm -f brad.bio.roff && ./bradman -i bio.vintage.yaml -o brad.bio.roff "
        "&& test -s brad.bio.roff && ls -l brad.bio.roff",
        _PROMPT,
        _CMD_TIMEOUT,
        label="run bradman",
    )
    _log("bradman run complete")

    # The VAX prepares the spool consumed by the PDP-11 stage.
    _log("Uuencoding: uuencode /tmp/brad.bio.roff brad.bio.roff > /tmp/brad.bio.uu")
    uu_out = run_checked(
        child,
        "rm -f /tmp/brad.bio.uu && uuencode /tmp/brad.bio.roff brad.bio.roff > /tmp/brad.bio.uu "
        "&& test -s /tmp/brad.bio.uu",
        _PROMPT,
        _CMD_TIMEOUT,
        label="uuencode brad.bio.roff",
    )
    _log("[uucp] brad.bio.roff spooled on VAX as brad.bio.uu")

    log_console_section("vax", "vax-run", strip_console(bradman_out + b"\n" + uu_out))


def _capture_spool(child: pexpect.spawn) -> str:
    """Capture the VAX-generated spool between marker-only console lines."""
    _log("[uucp] Capturing /tmp/brad.bio.uu from VAX spool…")
    child.sendline("stty -echo")
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)
    child.sendline("echo '__BRADBIOUU_BEGIN__'; cat /tmp/brad.bio.uu; echo '__BRADBIOUU_END__'; stty echo")
    child.expect(_CAPTURE_BEGIN, timeout=_CMD_TIMEOUT)
    child.expect(_CAPTURE_END, timeout=_CMD_TIMEOUT)
    raw_bytes: bytes = child.before
    child.expect(_PROMPT, timeout=_CMD_TIMEOUT)

    raw = raw_bytes.decode("ascii", errors="replace")
    return raw.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Run stage B and return its process exit code."""
    args = _parse_args(argv)

    bradman_path = Path(args.bradman)
    bio_yaml_path = Path(args.bio_yaml)
    for p in (bradman_path, bio_yaml_path):
        if not p.exists():
            _log(f"ERROR: input file not found: {p}")
            return 1

    bradman_c = bradman_path.read_text(encoding="ascii")
    bio_yaml = bio_yaml_path.read_text(encoding="ascii")
    _log(f"bradman.c: {len(bradman_c.splitlines())} lines")
    _log(f"bio.vintage.yaml: {len(bio_yaml.splitlines())} lines")

    simh_bin, ini_path, workdir = _resolve_simh_config(args)
    _log(f"Spawning: {simh_bin} {ini_path}  (cwd={workdir})")

    child = pexpect.spawn(
        simh_bin,
        [ini_path],
        cwd=workdir,
        timeout=_BOOT_TIMEOUT,
        encoding=None,
    )

    if args.verbose:
        child.logfile_read = sys.stderr.buffer

    try:
        _boot(child)
        _inject_file(child, "/tmp/bradman.c", bradman_c)
        # The summary can exceed the guest tty's 256-byte canonical line limit.
        _inject_file_uue(child, "/tmp/bio.vintage.yaml", bio_yaml.encode("ascii"))
        _compile_and_run(child)
        brad_bio_uu = _capture_spool(child)
        child.sendline("exit")
        # 4.3BSD can restart login after shell exit instead of returning EOF.
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
    except GuestCommandError as exc:
        _log(f"GUEST COMMAND FAILED: {exc}")
        return 1
    finally:
        if child.isalive():
            child.terminate(force=True)

    try:
        validate_uu_spool(brad_bio_uu)
    except ValueError as exc:
        _log(f"ERROR: UUE framing check failed: {exc}")
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
