"""Network testing utilities.

Functions for testing network connectivity and ports.
"""

import socket
import time
from typing import Optional


def wait_for_port(
    host: str,
    port: int,
    timeout: int = 30,
    check_interval: float = 0.5
) -> bool:
    """Wait for a TCP port to become available.

    Args:
        host: Hostname or IP address.
        port: Port number.
        timeout: Maximum time to wait in seconds.
        check_interval: Time between checks in seconds.

    Returns:
        True if port becomes available, False if timeout.
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return True
        except (socket.gaierror, socket.timeout):
            pass

        time.sleep(check_interval)

    return False


def test_udp_connectivity(
    host: str,
    port: int,
    timeout: int = 5
) -> bool:
    """Test UDP connectivity to a host.

    Note: UDP is connectionless, so this only verifies we can
    create a socket and send data. It does not guarantee the
    remote host is listening.

    Args:
        host: Hostname or IP address.
        port: Port number.
        timeout: Socket timeout in seconds.

    Returns:
        True if socket can be created and data sent.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        # Send test packet
        test_data = b'test'
        sock.sendto(test_data, (host, port))

        sock.close()
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP port is open.

    Args:
        host: Hostname or IP address.
        port: Port number.
        timeout: Connection timeout in seconds.

    Returns:
        True if port is open, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.gaierror, socket.timeout):
        return False
