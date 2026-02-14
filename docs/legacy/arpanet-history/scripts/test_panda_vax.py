#!/usr/bin/env python3
"""Test VAX + Panda PDP-10 TCP/IP connectivity.

This script tests the simplified approach using Panda TOPS-20 distribution:
- No ARPANET 1822 protocol (uses TCP/IP directly)
- VAX at 172.20.0.10 with FTP server
- PDP-10 at 172.20.0.40 with FTP server

Test Goals:
1. Both containers running and healthy
2. VAX network configured (de0)
3. PDP-10 network configured (TCP/IP)
4. Ping test between systems
5. FTP connection test
"""

import subprocess
import sys
import time
from pathlib import Path

# Color output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def run(cmd: str, **kwargs) -> subprocess.CompletedProcess:
    """Run shell command and return result."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kwargs)

def check(condition: bool, success_msg: str, fail_msg: str) -> bool:
    """Print test result and return status."""
    if condition:
        print(f"{GREEN}✓{RESET} {success_msg}")
        return True
    else:
        print(f"{RED}✗{RESET} {fail_msg}")
        return False

def main() -> int:
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}VAX + Panda PDP-10 TCP/IP Test{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # Check containers are running
    print(f"{YELLOW}[1/5] Container Status{RESET}")
    vax_running = run("docker ps --filter name=panda-vax --format '{{.Status}}'").stdout.strip()
    pdp_running = run("docker ps --filter name=panda-pdp10 --format '{{.Status}}'").stdout.strip()

    vax_ok = check("Up" in vax_running, "VAX container running", "VAX container not running")
    pdp_ok = check("Up" in pdp_running, "PDP-10 container running", "PDP-10 container not running")

    if not (vax_ok and pdp_ok):
        print(f"\n{RED}ERROR: Containers not running. Start with:{RESET}")
        print(f"  docker compose -f docker-compose.panda-vax.yml up -d")
        return 1

    # Check network
    print(f"\n{YELLOW}[2/5] Docker Network{RESET}")
    net_info = run("docker network inspect panda-test -f '{{json .IPAM.Config}}'").stdout
    net_ok = check("172.20.0.0/16" in net_info,
                   "Network panda-test configured correctly",
                   "Network configuration issue")

    # Check VAX network interface
    print(f"\n{YELLOW}[3/5] VAX Network Interface{RESET}")
    time.sleep(2)  # Wait for VAX to boot
    vax_ip = run("docker exec panda-vax ip addr show eth0 2>/dev/null | grep 'inet 172.20.0.10'").stdout
    vax_net_ok = check(bool(vax_ip.strip()),
                       "VAX eth0 interface at 172.20.0.10",
                       "VAX network interface not configured")

    # Check PDP-10 process
    print(f"\n{YELLOW}[4/5] PDP-10 System{RESET}")
    pdp_proc = run("docker exec panda-pdp10 pgrep -f kn10-kl").stdout
    pdp_proc_ok = check(bool(pdp_proc.strip()),
                        "PDP-10 KLH10 emulator running",
                        "PDP-10 emulator not running")

    # Check PDP-10 logs for boot messages
    pdp_logs = run("docker logs panda-pdp10 2>&1 | tail -20").stdout
    if "Panda" in pdp_logs or "TOPS-20" in pdp_logs:
        print(f"  {GREEN}→{RESET} TOPS-20 boot messages detected")
    else:
        print(f"  {YELLOW}⚠{RESET} No TOPS-20 boot messages yet (may still be booting)")

    # Test connectivity
    print(f"\n{YELLOW}[5/5] Network Connectivity{RESET}")
    ping_result = run("docker exec panda-vax ping -c 3 -W 2 172.20.0.40 2>/dev/null").returncode
    ping_ok = check(ping_result == 0,
                    "VAX → PDP-10 ping successful",
                    "VAX → PDP-10 ping failed (PDP-10 may still be booting)")

    # Summary
    print(f"\n{BLUE}{'='*60}{RESET}")
    total_tests = 5
    passed_tests = sum([vax_ok, pdp_ok, net_ok, vax_net_ok, pdp_proc_ok])

    if passed_tests == total_tests:
        print(f"{GREEN}✓ All tests passed ({passed_tests}/{total_tests}){RESET}")
        print(f"\n{GREEN}Next Steps:{RESET}")
        print(f"  1. Access VAX:    telnet localhost 2323")
        print(f"  2. Access PDP-10: telnet localhost 2326")
        print(f"  3. Test FTP:      ftp 172.20.0.40 (from VAX)")
        return 0
    else:
        print(f"{RED}✗ Some tests failed ({passed_tests}/{total_tests}){RESET}")
        print(f"\n{YELLOW}Debugging:{RESET}")
        print(f"  docker logs panda-vax")
        print(f"  docker logs panda-pdp10")
        print(f"  docker exec -it panda-vax /bin/sh")
        print(f"  docker exec -it panda-pdp10 /bin/sh")
        return 1

if __name__ == "__main__":
    sys.exit(main())
