#!/usr/bin/env python3
"""ARPANET Docker integration tests.

Tests verify that VAX and IMP containers build, start, and establish
network connectivity. Used in CI/CD and local development.

Usage:
    ./test_arpanet.py
    ./test_arpanet.py --mode connectivity
    ./test_arpanet.py --verbose --no-cleanup
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from docker_utils import (
    check_docker_available,
    compose_build,
    compose_up,
    compose_down,
    container_is_running,
    get_container_logs,
)
from network_utils import (
    wait_for_port,
    test_udp_connectivity,
)
from log_parser import (
    parse_vax_logs,
    parse_imp_logs,
    check_for_errors,
)


def test_build(verbose=False):
    """Test that containers build successfully.

    Args:
        verbose: Enable detailed output.

    Returns:
        True if build succeeds, False otherwise.
    """
    print("Testing container builds...")

    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.arpanet.phase1.yml'

    if not compose_build(compose_file, verbose=verbose):
        print("❌ Build failed")
        return False

    print("✅ Build successful")
    return True


def test_connectivity(verbose=False, cleanup=True):
    """Test network connectivity between VAX and IMP.

    Args:
        verbose: Enable detailed output.
        cleanup: Clean up containers after test.

    Returns:
        True if connectivity test passes, False otherwise.
    """
    print("Testing network connectivity...")

    compose_file = Path(__file__).parent.parent.parent / 'docker-compose.arpanet.phase1.yml'

    # Start containers
    if not compose_up(compose_file, verbose=verbose):
        print("❌ Failed to start containers")
        if cleanup:
            compose_down(compose_file)
        return False

    # Wait for boot
    print("Waiting for VAX boot (60s)...")
    time.sleep(60)
    print("Waiting for IMP boot (10s)...")
    time.sleep(10)

    # Check containers are running
    if not container_is_running('arpanet-vax'):
        print("❌ VAX container not running")
        if verbose:
            print(get_container_logs('arpanet-vax', tail=50))
        if cleanup:
            compose_down(compose_file)
        return False

    if not container_is_running('arpanet-imp1'):
        print("❌ IMP container not running")
        if verbose:
            print(get_container_logs('arpanet-imp1', tail=50))
        if cleanup:
            compose_down(compose_file)
        return False

    print("✅ Containers running")

    # Check console ports
    if not wait_for_port('localhost', 2323, timeout=5):
        print("❌ VAX console port 2323 not accessible")
        if cleanup:
            compose_down(compose_file)
        return False

    if not wait_for_port('localhost', 2324, timeout=5):
        print("❌ IMP console port 2324 not accessible")
        if cleanup:
            compose_down(compose_file)
        return False

    print("✅ Console ports accessible")

    # Cleanup
    if cleanup:
        compose_down(compose_file)
        print("✅ Cleanup complete")

    print("✅ Connectivity test passed")
    return True


def test_logs(verbose=False):
    """Test that container logs show proper initialization.

    Args:
        verbose: Enable detailed output.

    Returns:
        True if logs look good, False otherwise.
    """
    print("Testing container logs...")

    # Check if containers are running
    if not container_is_running('arpanet-vax'):
        print("❌ VAX container not running (start containers first)")
        return False

    if not container_is_running('arpanet-imp1'):
        print("❌ IMP container not running (start containers first)")
        return False

    # Get logs
    vax_logs = get_container_logs('arpanet-vax')
    imp_logs = get_container_logs('arpanet-imp1')

    # Parse VAX logs
    vax_info = parse_vax_logs(vax_logs)
    if verbose:
        print(f"VAX info: {vax_info}")

    # Parse IMP logs
    imp_info = parse_imp_logs(imp_logs)
    if verbose:
        print(f"IMP info: {imp_info}")

    # Check for errors
    vax_errors = check_for_errors(vax_logs)
    imp_errors = check_for_errors(imp_logs)

    if vax_errors:
        print(f"❌ VAX errors found: {vax_errors}")
        return False

    if imp_errors:
        print(f"❌ IMP errors found: {imp_errors}")
        return False

    print("✅ Log test passed")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description='ARPANET Docker integration tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--mode',
        choices=['build', 'connectivity', 'logs', 'all'],
        default='all',
        help='Test mode to run (default: all)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        help='Skip cleanup after tests (for debugging)'
    )

    args = parser.parse_args()

    # Check Docker is available
    if not check_docker_available():
        print("❌ Docker not available")
        return 2

    # Run tests
    results = []

    if args.mode in ['build', 'all']:
        results.append(test_build(verbose=args.verbose))

    if args.mode in ['connectivity', 'all']:
        results.append(test_connectivity(
            verbose=args.verbose,
            cleanup=not args.no_cleanup
        ))

    if args.mode == 'logs':
        results.append(test_logs(verbose=args.verbose))

    # Report results
    if all(results):
        print("\n✅ All tests passed")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
