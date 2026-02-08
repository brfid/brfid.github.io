#!/usr/bin/env python3
"""IMP log collection test script.

Tests the IMP collectors by collecting logs from IMP1 and IMP2,
parsing ARPANET 1822 protocol messages, and displaying tagged events.

Usage:
    python arpanet/scripts/test_imp_logging.py
"""

import json
import subprocess
import sys
from itertools import islice
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from arpanet.scripts.test_utils import (
    check_containers_running,
    fail_with_message,
    get_docker_client,
    print_error,
    print_header,
    print_info,
    print_next_steps,
    print_step,
    print_success,
)


def run_log_collection(build_id: str, duration: int) -> None:
    """Run arpanet_logging collect command.

    Args:
        build_id: Build identifier for log collection
        duration: Duration in seconds to collect logs

    Raises:
        subprocess.CalledProcessError: If collection fails
    """
    cmd = [
        sys.executable,
        "-m",
        "arpanet_logging",
        "collect",
        "--build-id",
        build_id,
        "--components",
        "imp1",
        "imp2",
        "--duration",
        str(duration),
        "--phase",
        "phase2",
    ]

    print_info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, cwd=PROJECT_ROOT, capture_output=True, text=True,
        check=True  # Raises CalledProcessError on non-zero exit  # noqa: S603
    )

    print_success("Log collection completed")
    print(result.stdout)


def show_build_summary(build_id: str) -> None:
    """Show build summary using arpanet_logging show.

    Args:
        build_id: Build identifier
    """
    cmd = [sys.executable, "-m", "arpanet_logging", "show", build_id]

    print_info(f"Build Summary for: {build_id}")
    result = subprocess.run(  # noqa: S603
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print_error(f"Failed to show build summary: {result.stderr}")


def count_events(build_dir: Path, component: str) -> dict:
    """Count tagged events in component logs.

    Args:
        build_dir: Build directory path
        component: Component name (e.g., 'imp1', 'imp2')

    Returns:
        Dictionary of event type counts
    """
    events_file = build_dir / component / "events.jsonl"

    if not events_file.exists():
        return {}

    counts = {
        "modem-interface": 0,
        "host-interface": 0,
        "packet": 0,
        "total": 0,
    }

    with open(events_file) as f:
        for line in f:
            counts["total"] += 1
            if "modem-interface" in line:
                counts["modem-interface"] += 1
            if "host-interface" in line:
                counts["host-interface"] += 1
            if "packet" in line:
                counts["packet"] += 1

    return counts


def print_event_summary(build_dir: Path, component: str) -> None:
    """Print summary of events for a component.

    Args:
        build_dir: Build directory path
        component: Component name
    """
    events_file = build_dir / component / "events.jsonl"

    if not events_file.exists():
        print_info(f"No events file found for {component}")
        return

    print_info(f"{component.upper()} events:")

    # Read first 10 events
    with events_file.open(encoding="utf-8") as f:
        lines = list(islice(f, 10))

    print("  First 10 events:")
    for i, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
            tags = event.get("tags", [])
            print(f"    {i}. {', '.join(tags)}")
        except (json.JSONDecodeError, KeyError):
            print(f"    {i}. {line[:80]}...")

    print(f"  Total {component} events: {count_events(build_dir, component)['total']}")


def main() -> int:
    """Run IMP log collection tests.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("ARPANET IMP Log Collection Test")

    # Get Docker client
    client = get_docker_client()

    # Step 1: Check containers are running
    print_step(1, "Checking container status...")
    required_containers = ["arpanet-imp1", "arpanet-imp2"]

    if not check_containers_running(client, required_containers):
        fail_with_message(
            "IMP containers not running",
            "Start with: docker compose -f docker-compose.arpanet.phase2.yml up -d"
        )

    print_success("Both IMP containers are running")
    print()

    # Step 2: Run log collection
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    build_id = f"test-imp-{timestamp}"
    duration = 30

    print_step(2, f"Collecting logs for {duration} seconds...")
    print_info(f"Build ID: {build_id}")
    print_info("Components: imp1, imp2")
    print()

    try:
        run_log_collection(build_id, duration)
    except subprocess.CalledProcessError:
        return 1

    print()

    # Step 3: Show build summary
    print_step(3, "Showing build summary...")
    show_build_summary(build_id)
    print()

    # Step 4: Analyze events
    print_step(4, "Analyzing IMP events...")

    # Determine log directory
    log_dirs = [
        Path("/mnt/arpanet-logs"),
        PROJECT_ROOT / "logs",
    ]

    build_dir = None
    for log_dir in log_dirs:
        candidate = log_dir / "builds" / build_id
        if candidate.exists():
            build_dir = candidate
            break

    if build_dir:
        print_info(f"Logs directory: {build_dir}")
        print()

        # IMP1 events
        print_event_summary(build_dir, "imp1")
        print()

        # IMP2 events
        print_event_summary(build_dir, "imp2")
        print()
    else:
        print_error(f"Build directory not found for: {build_id}")
        print_info(f"Expected at: {log_dirs[0] / 'builds' / build_id}")
        print()

    print_success("IMP log collection test complete!")
    if build_dir:
        print_info(f"Logs stored in: {build_dir}")
    else:
        print_info("Logs stored in: unavailable (build directory not found)")
    print()

    print_next_steps([
        "Review parsed ARPANET 1822 protocol events",
        "Check for packet routing patterns between IMPs",
        "Analyze timing and sequence of interface events",
    ])

    return 0


if __name__ == "__main__":
    sys.exit(main())
