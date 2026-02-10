#!/usr/bin/env python3
"""Collect native-first HI1 framing mismatch evidence from a running Phase 2 stack.

This script is intentionally *non-orchestrating*: it does not start/stop Docker
services. It only inspects already-running containers so we avoid duplicating
infrastructure (especially long-lived AWS test environments).

Usage:
    python arpanet/scripts/test_phase2_hi1_framing.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arpanet.scripts.test_utils import (
    check_containers_running,
    fail_with_message,
    get_container,
    get_container_logs,
    get_docker_client,
    print_error,
    print_header,
    print_info,
    print_step,
    print_success,
)


BAD_MAGIC_RE = re.compile(r"bad magic number \(magic=([0-9a-fA-F]+)\)")
HI1_RE = re.compile(r"HI1 UDP:.*", re.IGNORECASE)


def _positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return ivalue


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect non-orchestrating HI1 framing mismatch evidence from running Phase 2 containers."
    )
    parser.add_argument(
        "--imp2-tail",
        type=_positive_int,
        default=2000,
        help="Number of IMP2 log lines to inspect (default: 2000)",
    )
    parser.add_argument(
        "--pdp10-tail",
        type=_positive_int,
        default=500,
        help="Number of PDP-10 log lines to inspect (default: 500)",
    )
    parser.add_argument(
        "--sample-limit",
        type=_positive_int,
        default=20,
        help="Maximum HI1 and marker lines to include in artifact sections (default: 20)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional artifact output path. Defaults to build/arpanet/analysis/hi1-framing-matrix-<timestamp>.md",
    )
    return parser.parse_args(argv)


def _artifact_path() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    out_dir = Path("build") / "arpanet" / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"hi1-framing-matrix-{ts}.md"


def _write_artifact(
    output_path: Path,
    bad_magic_counts: Counter[str],
    hi1_samples: list[str],
    pdp10_summary_lines: list[str],
    capture_notes: list[str] | None = None,
) -> None:
    lines: list[str] = []
    lines.append("# HI1 Native-First Framing Evidence")
    lines.append("")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("- Source: running `arpanet-imp2` and `arpanet-pdp10` container logs")
    lines.append("- Mode: non-orchestrating (no compose up/down)")
    if capture_notes:
        lines.extend([f"- {note}" for note in capture_notes])
    lines.append("")

    lines.append("## Bad-Magic Summary")
    lines.append("")
    if bad_magic_counts:
        lines.append("| magic | count |")
        lines.append("|---|---:|")
        for magic, count in bad_magic_counts.most_common():
            lines.append(f"| `{magic}` | {count} |")
    else:
        lines.append("No `bad magic` markers detected in inspected IMP2 logs.")
    lines.append("")

    lines.append("## IMP2 HI1 Sample Lines")
    lines.append("")
    if hi1_samples:
        lines.append("```text")
        lines.extend(hi1_samples)
        lines.append("```")
    else:
        lines.append("No HI1 UDP lines captured in inspected log window.")
    lines.append("")

    lines.append("## PDP-10 Runtime Markers")
    lines.append("")
    if pdp10_summary_lines:
        lines.append("```text")
        lines.extend(pdp10_summary_lines)
        lines.append("```")
    else:
        lines.append("No key IMP runtime markers found in inspected PDP-10 log window.")
    lines.append("")

    lines.append("## Interpretation")
    lines.append("")
    if bad_magic_counts:
        lines.append(
            "IMP2 HI1 is receiving ingress packets but rejecting framing at the parser boundary "
            "(`bad magic`). This keeps focus on native header-contract compatibility work."
        )
        if any(m in bad_magic_counts for m in ("feffffff", "00000219", "ffffffff")):
            lines.append("")
            lines.append(
                "Observed magic patterns include values previously correlated with Ethernet/ARP-style "
                "payloads on the KS-10 path. Prioritize native host-link/header-contract validation "
                "before considering any fallback framing adapter."
            )
    else:
        lines.append(
            "No bad-magic evidence in this capture window; re-run during active PDP-10 IMP traffic "
            "or increase log tail depth."
        )
    lines.append("")

    output_path.write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else [])

    print_header("ARPANET Phase 2 HI1 Framing Evidence", "(native-first, non-orchestrating)")

    client = get_docker_client()

    print_step(1, "Checking required running containers...")
    required_containers = ["arpanet-imp2", "arpanet-pdp10"]
    if not check_containers_running(client, required_containers):
        fail_with_message(
            "Required containers are not running",
            "Not auto-starting to avoid duplicating infrastructure. "
            "Use existing Phase 2 stack, then rerun this script.",
        )
    print_success("IMP2 and PDP-10 containers are running")
    print()

    imp2 = get_container(client, "arpanet-imp2")
    pdp10 = get_container(client, "arpanet-pdp10")
    if not imp2 or not pdp10:
        fail_with_message("Failed to get container objects")

    print_step(2, "Collecting and parsing IMP2 HI1 logs...")
    imp2_logs = get_container_logs(imp2, tail=args.imp2_tail)
    hi1_lines = [line for line in imp2_logs.splitlines() if HI1_RE.search(line)]
    bad_magic_values = [m.group(1).lower() for m in BAD_MAGIC_RE.finditer(imp2_logs)]
    bad_magic_counts = Counter(bad_magic_values)

    if bad_magic_counts:
        print_success("Detected HI1 bad-magic markers")
        for magic, count in bad_magic_counts.most_common():
            print_info(f"  magic={magic} count={count}")
    else:
        print_error("No bad-magic markers found in inspected IMP2 log window")
    print()

    print_step(3, "Collecting PDP-10 IMP runtime markers...")
    pdp10_logs = get_container_logs(pdp10, tail=args.pdp10_tail)
    pdp10_markers = [
        line
        for line in pdp10_logs.splitlines()
        if any(
            marker in line.lower()
            for marker in (
                "imp network interface",
                "attach imp",
                "imp dhcp",
                "opened os device",
                "dskdmp",
            )
        )
    ]
    print_success(f"Captured {len(pdp10_markers)} PDP-10 marker lines")
    print()

    print_step(4, "Writing HI1 mismatch artifact...")
    out_path = args.output or _artifact_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_artifact(
        out_path,
        bad_magic_counts=bad_magic_counts,
        hi1_samples=hi1_lines[: args.sample_limit],
        pdp10_summary_lines=pdp10_markers[: args.sample_limit],
        capture_notes=[
            f"IMP2 log tail: {args.imp2_tail}",
            f"PDP-10 log tail: {args.pdp10_tail}",
            f"Sample limit: {args.sample_limit}",
        ],
    )
    print_success(f"Wrote evidence artifact: {out_path}")
    print()

    print_info("Next: append artifact findings into arpanet/PHASE3-PROGRESS.md Session notes.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
