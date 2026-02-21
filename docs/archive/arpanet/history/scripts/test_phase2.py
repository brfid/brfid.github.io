#!/usr/bin/env python3
"""ARPANET Phase 2 link test script.

Validates VAX + IMP1 + IMP2 + PDP-10 topology with multi-hop routing.
Tests modem interface (IMP-to-IMP) and host interface (IMP-to-host) links.

Usage:
    python arpanet/scripts/test_phase2.py
"""

import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arpanet.scripts.test_utils import (
    check_containers_running,
    check_logs_for_pattern,
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
    """Run Phase 2 link tests.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print_header(
        "ARPANET Phase 2 Link Test",
        "(VAX + IMP1 + IMP2 + PDP10)"
    )

    # Get Docker client
    client = get_docker_client()

    # Step 1: Check containers are running
    print_step(1, "Checking if phase 2 containers are running...")
    required_containers = [
        "arpanet-vax",
        "arpanet-imp1",
        "arpanet-imp2",
        "arpanet-pdp10",
        "arpanet-hi1shim",
    ]

    if not check_containers_running(client, required_containers):
        fail_with_message(
            "Required containers not running",
            "Start with: docker compose -f docker-compose.arpanet.phase2.yml up -d"
        )

    print_success("VAX, IMP1, IMP2, PDP10, and Host-IMP Interface containers are running")
    print()

    # Get container objects
    vax = get_container(client, "arpanet-vax")
    imp1 = get_container(client, "arpanet-imp1")
    imp2 = get_container(client, "arpanet-imp2")
    pdp10 = get_container(client, "arpanet-pdp10")
    hi1shim = get_container(client, "arpanet-hi1shim")

    if not all([vax, imp1, imp2, pdp10, hi1shim]):
        fail_with_message("Failed to get container objects")

    # Step 2: Check assigned IPs
    print_step(2, "Checking assigned container IPs...")
    ips = {
        "VAX": get_container_ip(vax),
        "IMP1": get_container_ip(imp1),
        "IMP2": get_container_ip(imp2),
        "PDP10": get_container_ip(pdp10),
        "HI1SHIM": get_container_ip(hi1shim),
    }

    for name, ip in ips.items():
        print_info(f"{name:6s}: {ip}")

    # Validate expected IPs
    expected = {
        "VAX": "172.20.0.10",
        "IMP1": "172.20.0.20",
        "IMP2": "172.20.0.30",
        "PDP10": "172.20.0.40",
        "HI1SHIM": "172.20.0.50",
    }

    all_ips_correct = True
    for name, expected_ip in expected.items():
        if ips[name] != expected_ip:
            print_error(f"{name} IP mismatch (expected {expected_ip}, got {ips[name]})")
            all_ips_correct = False

    if all_ips_correct:
        print_success("All IP addresses match expected values")
    print()

    # Step 3: Check IMP1 modem-link configuration
    print_step(3, "Checking IMP1 modem-link configuration evidence...")
    imp1_patterns = [r"MI1", r"3001", r"IMP #1 \(Phase 2\)"]
    imp1_ok = any(check_logs_for_pattern(imp1, pattern) for pattern in imp1_patterns)

    if imp1_ok:
        print_success("IMP1 logs show MI1/Phase 2 startup markers")
    else:
        print_error("IMP1 logs do not show expected MI1 markers")
        return 1
    print()

    # Step 4: Check IMP2 modem-link configuration
    print_step(4, "Checking IMP2 modem-link configuration evidence...")
    imp2_patterns = [r"MI1", r"3001", r"IMP #2 \(Phase 2\)"]
    imp2_ok = any(check_logs_for_pattern(imp2, pattern) for pattern in imp2_patterns)

    if imp2_ok:
        print_success("IMP2 logs show MI1/Phase 2 startup markers")
    else:
        print_error("IMP2 logs do not show expected MI1 markers")
        return 1
    print()

    # Step 5: Check IMP2 host-link (HI1) configuration
    print_step(5, "Checking IMP2 host-link (HI1) configuration evidence...")
    imp2_hi1_patterns = [r"HI1", r"172\.20\.0\.50", r"Host-IMP Interface"]
    imp2_hi1_ok = any(
        check_logs_for_pattern(imp2, pattern) for pattern in imp2_hi1_patterns
    )

    if imp2_hi1_ok:
        print_success("IMP2 logs show HI1 host-link startup markers")
    else:
        print_error("IMP2 logs do not show expected HI1 host-link markers")
        return 1
    print()

    # Step 6: Recent IMP log tails
    print_step(6, "Recent IMP log tails for manual inspection...")
    print()
    print("--- IMP1 tail ---")
    print(get_container_logs(imp1, tail=20))
    print()
    print("--- IMP2 tail ---")
    print(get_container_logs(imp2, tail=20))
    print()

    print_success("Phase 2 link test completed.")
    print()

    print_next_steps([
        "telnet localhost 2324   # IMP1 console",
        "telnet localhost 2325   # IMP2 console",
        "docker logs arpanet-hi1shim | tail -20  # Host-IMP Interface activity",
        "docker logs arpanet-pdp10 | tail -20  # PDP10 activity",
        "Look for MI1 modem traffic and HI1 host-link markers in IMP logs",
    ])

    return 0


if __name__ == "__main__":
    sys.exit(main())
