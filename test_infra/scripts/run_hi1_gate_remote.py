#!/usr/bin/env python3
"""Run strict Phase 2 HI1 gate against the active AWS test instance.

This helper is intentionally non-interactive:
- discovers the instance SSH command from CloudFormation outputs
- syncs the latest local HI1 gate script to the remote workspace
- executes strict gate parameters remotely
- prints JSON summary (if present)
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path


STACK_NAME = "ArpanetTestStack"
REMOTE_REPO = "/home/ubuntu/brfid.github.io"
REMOTE_SCRIPT = f"{REMOTE_REPO}/arpanet/scripts/test_phase2_hi1_framing.py"
REMOTE_JSON = f"{REMOTE_REPO}/build/arpanet/analysis/hi1-framing-matrix-latest.json"
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


def main() -> int:
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
    gate = subprocess.run(["ssh", "-i", key_path, target, remote_gate], capture_output=True, text=True)
    if gate.stdout:
        print(gate.stdout, end="")
    if gate.stderr:
        print(gate.stderr, end="", file=sys.stderr)

    print(f"REMOTE_GATE_EXIT_CODE={gate.returncode}")

    json_cmd = f"if [ -f {REMOTE_JSON} ]; then cat {REMOTE_JSON}; fi"
    summary = subprocess.run(["ssh", "-i", key_path, target, json_cmd], capture_output=True, text=True)
    if summary.stdout.strip():
        print("---REMOTE_HI1_JSON---")
        print(summary.stdout.strip())

    return gate.returncode


if __name__ == "__main__":
    raise SystemExit(main())
