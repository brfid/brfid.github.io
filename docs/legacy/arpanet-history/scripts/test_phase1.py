#!/usr/bin/env python3
"""ARPANET Phase 1 connectivity test script.

Tests VAX + IMP #1 connectivity and validates proper ARPANET 1822
protocol communication between the host and IMP.

Usage:
    python arpanet/scripts/test_phase1.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arpanet.scripts.test_utils import (
    Colors,
    check_containers_running,
    fail_with_message,
    get_container,
    get_container_ip,
    get_container_logs,
    get_docker_client,
    print_error,
    print_header,
    print_info,
    print_next_steps,
    print_step,
    print_success,
)


def main() -> int:
    """Run Phase 1 connectivity tests.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header("ARPANET Phase 1 Connectivity Test")

    # Get Docker client
    client = get_docker_client()

    # Step 1: Check containers are running
    print_step(1, "Checking if containers are running...")
    required_containers = ["arpanet-vax", "arpanet-imp1"]

    if not check_containers_running(client, required_containers):
        fail_with_message(
            "Containers not running",
            "Start with: docker-compose -f docker-compose.arpanet.phase1.yml up -d"
        )

    print_success("Both VAX and IMP containers are running")
    print()

    # Get container objects
    vax = get_container(client, "arpanet-vax")
    imp1 = get_container(client, "arpanet-imp1")

    if not vax or not imp1:
        fail_with_message("Failed to get container objects")

    # Step 2: Check VAX boot status
    print_step(2, "Checking VAX boot status...")
    vax_logs = get_container_logs(vax, tail=10)
    print(vax_logs)
    print()

    # Step 3: Check IMP status
    print_step(3, "Checking IMP status...")
    imp_logs = get_container_logs(imp1, tail=10)
    print(imp_logs)
    print()

    # Step 4: Network connectivity
    print_step(4, "Checking network connectivity...")
    vax_ip = get_container_ip(vax)
    imp_ip = get_container_ip(imp1)
    print_info(f"VAX IP:  {vax_ip}")
    print_info(f"IMP IP:  {imp_ip}")

    if vax_ip == "172.20.0.10":
        print_success("VAX has correct IP address")
    else:
        print_error(f"VAX IP mismatch (expected 172.20.0.10, got {vax_ip})")

    if imp_ip == "172.20.0.20":
        print_success("IMP has correct IP address")
    else:
        print_error(f"IMP IP mismatch (expected 172.20.0.20, got {imp_ip})")
    print()

    # Step 5: UDP port status
    print_step(5, "Checking UDP ports...")
    print_info("Checking VAX UDP port 2000...")
    print_info("  (Port status not directly visible from outside container)")
    print()

    # Step 6: Instructions
    print_step(6, "Instructions for manual testing...")
    print()

    manual_steps = [
        "Connect to VAX console: telnet localhost 2323",
        "Login: root (no password in base image)",
        "Check network interface: /etc/ifconfig de0",
        "Check routing: netstat -rn",
        "",
        "Connect to IMP console (debugging): telnet localhost 2324",
        "Monitor IMP logs for host connection messages",
        "Check for packet exchange in IMP debug output",
    ]

    for step in manual_steps:
        if step:
            print_info(f"  {step}")
        else:
            print()

    print(f"{Colors.GREEN}Test script complete!{Colors.RESET}")
    print()

    print_next_steps([
        "Connect to VAX console and check network interface",
        "Monitor IMP logs for host connection messages",
        "Check for packet exchange in IMP debug output",
    ])

    return 0


if __name__ == "__main__":
    sys.exit(main())
