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
    parser.add_argument(
        "--imp-mode",
        choices=["simp", "uni"],
        default=None,
        help="Optionally force remote phase2 pdp10.ini IMP mode before running gate",
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


def _compute_delta_counts(
    steady_counts: dict[str, object] | None,
    restart_counts: dict[str, object] | None,
) -> dict[str, int]:
    steady = {str(k): int(v) for k, v in (steady_counts or {}).items()}
    restart = {str(k): int(v) for k, v in (restart_counts or {}).items()}
    keys = set(steady) | set(restart)
    return {k: max(0, restart.get(k, 0) - steady.get(k, 0)) for k in sorted(keys)}


def _set_remote_imp_mode(ssh_key: str, target: str, mode: str) -> bool:
    # Keep this narrowly scoped to the phase2 pdp10.ini baseline line.
    cmd = (
        f"cd {REMOTE_REPO} && "
        "python3 - <<'PY'\n"
        "from pathlib import Path\n"
        "p = Path('arpanet/configs/phase2/pdp10.ini')\n"
        "text = p.read_text()\n"
        f"text = text.replace('set imp simp', 'set imp {mode}')\n"
        f"text = text.replace('set imp uni', 'set imp {mode}')\n"
        "p.write_text(text)\n"
        "print('updated', p)\n"
        "PY"
    )
    result = _run_remote(ssh_key, target, cmd)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not LOCAL_SCRIPT.exists():
        print(f"❌ Local script not found: {LOCAL_SCRIPT}", file=sys.stderr)
        return 1

    ssh_command = _get_ssh_command()
    key_path, target = _parse_ssh_command(ssh_command)

    if args.imp_mode:
        print(f"Setting remote pdp10.ini IMP mode to: {args.imp_mode}")
        ok = _set_remote_imp_mode(key_path, target, args.imp_mode)
        if not ok:
            print("❌ Failed to update remote IMP mode", file=sys.stderr)
            return 1
        # Apply config change before evidence collection.
        print("Restarting arpanet-pdp10 to apply updated IMP mode...")
        mode_restart = _run_remote(key_path, target, "docker restart arpanet-pdp10 >/dev/null")
        if mode_restart.returncode != 0:
            if mode_restart.stderr:
                print(mode_restart.stderr, end="", file=sys.stderr)
            print("❌ Failed to restart arpanet-pdp10 after IMP mode update", file=sys.stderr)
            return 1
        if args.restart_sleep > 0:
            _run_remote(key_path, target, f"sleep {args.restart_sleep}")

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

    delta_summary: dict[str, object] | None = None
    if args.dual_window:
        steady_counts = (steady_summary or {}).get("bad_magic_counts") if isinstance(steady_summary, dict) else {}
        restart_counts = (restart_summary or {}).get("bad_magic_counts") if isinstance(restart_summary, dict) else {}
        steady_total = int((steady_summary or {}).get("bad_magic_total", 0)) if isinstance(steady_summary, dict) else 0
        restart_total = int((restart_summary or {}).get("bad_magic_total", 0)) if isinstance(restart_summary, dict) else 0
        steady_hi1 = int((steady_summary or {}).get("hi1_line_count", 0)) if isinstance(steady_summary, dict) else 0
        restart_hi1 = int((restart_summary or {}).get("hi1_line_count", 0)) if isinstance(restart_summary, dict) else 0

        delta_counts = _compute_delta_counts(
            steady_counts if isinstance(steady_counts, dict) else {},
            restart_counts if isinstance(restart_counts, dict) else {},
        )
        delta_total = sum(delta_counts.values())
        delta_summary = {
            "bad_magic_counts_delta": delta_counts,
            "bad_magic_total_delta": delta_total,
            "bad_magic_unique_delta": sum(1 for v in delta_counts.values() if v > 0),
            "hi1_line_count_delta": max(0, restart_hi1 - steady_hi1),
            "steady_bad_magic_total": steady_total,
            "restart_bad_magic_total": restart_total,
            "steady_hi1_line_count": steady_hi1,
            "restart_hi1_line_count": restart_hi1,
            "method": "restart_minus_steady_within_same_dual_window_run",
        }

    manifest = {
        "dual_window": args.dual_window,
        "imp_mode": args.imp_mode,
        "steady_exit": gate.returncode,
        "restart_exit": restart_exit if args.dual_window else None,
        "steady_summary": steady_summary,
        "restart_summary": restart_summary,
        "delta_summary": delta_summary,
        "final_exit": final_exit,
    }
    print("---REMOTE_HI1_GATE_MANIFEST---")
    print(json.dumps(manifest, indent=2, sort_keys=True))

    return final_exit


if __name__ == "__main__":
    raise SystemExit(main())
