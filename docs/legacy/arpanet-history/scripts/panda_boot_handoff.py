#!/usr/bin/env python3
"""Automate KLH10 BOOT handoff through a real docker-attach TTY.

This avoids flaky host-mapped console ingress (localhost:2326) by writing
directly to the attached container console stream.
"""

from __future__ import annotations

import argparse
import os
import pty
import re
import select
import subprocess
import sys
import time


def _ts(start: float) -> str:
    return f"+{time.time() - start:0.2f}s"


def run_handoff(
    container: str,
    timeout_s: int,
    command_seq: list[str],
    require_prompt: bool,
) -> int:
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        ["docker", "attach", container],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    os.close(slave_fd)

    buffer = ""
    sent: list[str] = []
    idx = 0
    start = time.time()
    last_output = start
    sent_wakeup = False

    # Strict success criterion by default: real TOPS-20 command prompt.
    # Avoid false positives from log/banner text mentioning TOPS-20.
    prompt_re = re.compile(r"(?:^|\n)@")
    boot_seen = False

    try:
        while time.time() - start < timeout_s:
            rlist, _, _ = select.select([master_fd], [], [], 0.5)
            if rlist:
                data = os.read(master_fd, 4096)
                if not data:
                    break
                chunk = data.decode("utf-8", "ignore")
                buffer += chunk
                last_output = time.time()
                sys.stdout.write(chunk)
                sys.stdout.flush()

                if "BOOT V11" in buffer and not sent_wakeup:
                    boot_seen = True
                    os.write(master_fd, b"\r")
                    sent_wakeup = True
                    print(f"\n[{_ts(start)}] [handoff] sent wakeup CR after BOOT banner")
                    time.sleep(0.25)

                if ("BOOT>" in buffer or "BOOT V11" in buffer) and idx < len(command_seq):
                    cmd = command_seq[idx]
                    os.write(master_fd, cmd.encode("ascii", "ignore") + b"\r")
                    sent.append(cmd)
                    idx += 1
                    print(f"\n[{_ts(start)}] [handoff] sent {cmd}")
                    time.sleep(0.35)

                if (prompt_re.search(buffer) if require_prompt else (prompt_re.search(buffer) or "TOPS-20" in buffer)):
                    print(f"\n[{_ts(start)}] [handoff] detected login/command prompt")
                    return 0

            if proc.poll() is not None:
                break

            if idx > 0 and time.time() - last_output > 8:
                break

        print(f"\n[{_ts(start)}] [handoff] no success signature detected within timeout")
        return 2
    finally:
        try:
            # Docker detach sequence (Ctrl-P Ctrl-Q)
            os.write(master_fd, b"\x10\x11")
        except Exception:
            pass

        try:
            os.close(master_fd)
        except Exception:
            pass

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

        print("\n=== HANDOFF SUMMARY ===")
        print("boot_seen:", boot_seen)
        print("require_prompt:", require_prompt)
        print("sent_commands:", sent)
        print("tail:\n", buffer[-1800:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--container", default="panda-pdp10")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument(
        "--commands",
        default="/L,/G143",
        help="Comma-separated commands sent at BOOT>.",
    )
    parser.add_argument(
        "--require-at-prompt",
        action="store_true",
        default=True,
        help="Require a real TOPS-20 '@' prompt to declare success (default: true).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Number of bounded attach attempts.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Seconds between retries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    commands = [c.strip() for c in args.commands.split(",") if c.strip()]
    for attempt in range(1, max(1, args.retries) + 1):
        print(f"\n=== ATTEMPT {attempt}/{max(1, args.retries)} ===")
        rc = run_handoff(
            args.container,
            args.timeout,
            commands,
            require_prompt=args.require_at_prompt,
        )
        if rc == 0:
            return 0
        if attempt < max(1, args.retries):
            time.sleep(max(0.0, args.retry_delay))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
