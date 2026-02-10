#!/usr/bin/env python3
"""Run strict Phase 2 HI1 gate against the active AWS test instance.

This helper is intentionally non-interactive:
- discovers the instance SSH command from CloudFormation outputs
- syncs the latest local HI1 gate script to the remote workspace
- executes strict gate parameters remotely
- optionally executes a second restart-window run for dual-window validation
- prints JSON summary (if present)
"""

from __future__ import annotations

import json
import argparse
import shlex
import subprocess
import sys
from pathlib import Path


STACK_NAME = "ArpanetTestStack"
REMOTE_REPO = "/home/ubuntu/brfid.github.io"
REMOTE_SCRIPT = f"{REMOTE_REPO}/arpanet/scripts/test_phase2_hi1_framing.py"
REMOTE_JSON = f"{REMOTE_REPO}/build/arpanet/analysis/hi1-framing-matrix-latest.json"
REMOTE_JSON_RESTART = f"{REMOTE_REPO}/build/arpanet/analysis/hi1-framing-matrix-restart-window.json"
LOCAL_SCRIPT = Path(__file__).resolve().parents[2] / "arpanet" / "scripts" / "test_phase2_hi1_framing.py"


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _get_ssh_command() -> str:
    result = _run(
        ["aws", "cloudformation", "describe-stacks", "--stack-name", STACK_NAME],
        check=False,
    )
    if result.returncode != 0:
        print("❌ Failed to query CloudFormation stack outputs", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)

    stacks = json.loads(result.stdout).get("Stacks", [])
    if not stacks:
        print("❌ Stack not found", file=sys.stderr)
        sys.exit(1)

    outputs = {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}
    ssh_command = outputs.get("SSHCommand")
    if not ssh_command:
        print("❌ SSHCommand output missing from stack", file=sys.stderr)
        sys.exit(1)
    return ssh_command


def _parse_ssh_command(ssh_command: str) -> tuple[str, str]:
    parts = shlex.split(ssh_command)
    key_path = ""
    target = ""
    for i, part in enumerate(parts):
        if part == "-i" and i + 1 < len(parts):
            key_path = str(Path(parts[i + 1]).expanduser())
        if "@" in part and not part.startswith("-"):
            target = part

    if not key_path or not target:
        print(f"❌ Could not parse SSH command: {ssh_command}", file=sys.stderr)
        sys.exit(1)
    return key_path, target


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run remote HI1 strict gate on AWS test host")
    parser.add_argument(
        "--dual-window",
        action="store_true",
        help="Run both steady-state and restart-window checks",
    )
    parser.add_argument(
        "--restart-sleep",
        type=int,
        default=6,
        help="Seconds to wait after restarting arpanet-pdp10 in dual-window mode (default: 6)",
    )
    return parser.parse_args(argv)


def _run_remote(ssh_key: str, target: str, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["ssh", "-i", ssh_key, target, command], capture_output=True, text=True)


def _cat_remote_json(ssh_key: str, target: str, remote_json: str) -> dict[str, object] | None:
    show = _run_remote(
        ssh_key,
        target,
        f"if [ -f {remote_json} ]; then cat {remote_json}; fi",
    )
    payload = show.stdout.strip()
    if not payload:
        return None
    print(payload)
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not LOCAL_SCRIPT.exists():
        print(f"❌ Local script not found: {LOCAL_SCRIPT}", file=sys.stderr)
        return 1

    ssh_command = _get_ssh_command()
    key_path, target = _parse_ssh_command(ssh_command)

    print("Syncing latest HI1 gate script to AWS host...")
    scp_result = _run(["scp", "-i", key_path, str(LOCAL_SCRIPT), f"{target}:{REMOTE_SCRIPT}"], check=False)
    if scp_result.returncode != 0:
        print("❌ SCP failed", file=sys.stderr)
        print(scp_result.stderr.strip(), file=sys.stderr)
        return 1

    remote_gate = (
        f"cd {REMOTE_REPO} && "
        "python3 arpanet/scripts/test_phase2_hi1_framing.py "
        "--imp2-tail 5000 "
        "--pdp10-tail 1500 "
        "--sample-limit 50 "
        "--output build/arpanet/analysis/hi1-framing-matrix-latest.md "
        "--json-output build/arpanet/analysis/hi1-framing-matrix-latest.json "
        "--fail-on-bad-magic"
    )

    print("Running strict HI1 gate on AWS host...")
    gate = _run_remote(key_path, target, remote_gate)
    if gate.stdout:
        print(gate.stdout, end="")
    if gate.stderr:
        print(gate.stderr, end="", file=sys.stderr)

    print(f"REMOTE_GATE_EXIT_CODE={gate.returncode}")

    print("---REMOTE_HI1_JSON---")
    steady_summary = _cat_remote_json(key_path, target, REMOTE_JSON)

    final_exit = gate.returncode

    restart_summary: dict[str, object] | None = None
    restart_exit = 0
    if args.dual_window:
        restart_gate = (
            f"cd {REMOTE_REPO} && "
            "docker restart arpanet-pdp10 >/dev/null && "
            f"sleep {args.restart_sleep} && "
            "python3 arpanet/scripts/test_phase2_hi1_framing.py "
            "--imp2-tail 12000 "
            "--pdp10-tail 3000 "
            "--sample-limit 80 "
            "--output build/arpanet/analysis/hi1-framing-matrix-restart-window.md "
            "--json-output build/arpanet/analysis/hi1-framing-matrix-restart-window.json "
            "--fail-on-bad-magic"
        )
        print("Running restart-window HI1 gate on AWS host...")
        restart = _run_remote(key_path, target, restart_gate)
        if restart.stdout:
            print(restart.stdout, end="")
        if restart.stderr:
            print(restart.stderr, end="", file=sys.stderr)
        restart_exit = restart.returncode
        print(f"REMOTE_RESTART_WINDOW_EXIT_CODE={restart_exit}")

        print("---REMOTE_HI1_RESTART_JSON---")
        restart_summary = _cat_remote_json(key_path, target, REMOTE_JSON_RESTART)

        final_exit = gate.returncode if gate.returncode != 0 else restart_exit

    manifest = {
        "dual_window": args.dual_window,
        "steady_exit": gate.returncode,
        "restart_exit": restart_exit if args.dual_window else None,
        "steady_summary": steady_summary,
        "restart_summary": restart_summary,
        "final_exit": final_exit,
    }
    print("---REMOTE_HI1_GATE_MANIFEST---")
    print(json.dumps(manifest, indent=2, sort_keys=True))

    return final_exit


if __name__ == "__main__":
    raise SystemExit(main())
