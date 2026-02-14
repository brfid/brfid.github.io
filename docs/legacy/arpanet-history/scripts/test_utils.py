"""Shared utilities for ARPANET topology testing scripts.

Provides color output, Docker container checking, and common test patterns
for validating ARPANET topologies. Designed to replace bash test scripts
with more maintainable, testable Python code.
"""

import re
import sys
from typing import List, Optional

try:
    import docker
    from docker.models.containers import Container
except ImportError:
    print("Error: docker package not installed. Run: pip install docker")
    sys.exit(1)


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for formatted terminal output."""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    RESET = '\033[0m'


def print_header(title: str, subtitle: str = "") -> None:
    """Print a formatted test header.

    Args:
        title: Main title text
        subtitle: Optional subtitle text
    """
    print("=" * 45)
    print(title)
    if subtitle:
        print(subtitle)
    print("=" * 45)
    print()


def print_step(step_num: int, description: str) -> None:
    """Print a formatted test step header.

    Args:
        step_num: Step number
        description: Step description
    """
    print(f"{Colors.YELLOW}Step {step_num}: {description}{Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message in green.

    Args:
        message: Success message to display
    """
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message in red.

    Args:
        message: Error message to display
    """
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print an informational message.

    Args:
        message: Info message to display
    """
    print(message)


def get_docker_client() -> docker.DockerClient:
    """Get Docker client instance.

    Returns:
        Docker client

    Raises:
        docker.errors.DockerException: If Docker is not available
    """
    try:
        return docker.from_env()
    except Exception as e:
        print_error(f"Failed to connect to Docker: {e}")
        print_info("Make sure Docker is running and accessible")
        sys.exit(1)


def check_containers_running(
    client: docker.DockerClient,
    container_names: List[str]
) -> bool:
    """Check if all specified containers are running.

    Args:
        client: Docker client
        container_names: List of container names to check

    Returns:
        True if all containers are running, False otherwise
    """
    try:
        containers = client.containers.list()
        running_names = {c.name for c in containers}

        for name in container_names:
            if name not in running_names:
                return False
        return True
    except Exception as e:
        print_error(f"Failed to check container status: {e}")
        return False


def get_container(
    client: docker.DockerClient,
    name: str
) -> Optional[Container]:
    """Get a container by name.

    Args:
        client: Docker client
        name: Container name

    Returns:
        Container object or None if not found
    """
    try:
        return client.containers.get(name)
    except docker.errors.NotFound:
        return None
    except Exception as e:
        print_error(f"Error getting container {name}: {e}")
        return None


def get_container_ip(container: Container) -> str:
    """Get container IP address.

    Args:
        container: Container object

    Returns:
        IP address or "unknown" if not found
    """
    try:
        networks = container.attrs["NetworkSettings"]["Networks"]
        for network_data in networks.values():
            ip = network_data.get("IPAddress")
            if ip:
                return ip
        return "unknown"
    except (KeyError, TypeError):
        return "unknown"


def get_container_logs(
    container: Container,
    tail: int = 10
) -> str:
    """Get recent container logs.

    Args:
        container: Container object
        tail: Number of lines to retrieve

    Returns:
        Container logs as string
    """
    try:
        logs = container.logs(tail=tail, timestamps=False)
        return logs.decode('utf-8', errors='replace')
    except Exception as e:
        return f"Error getting logs: {e}"


def check_logs_for_pattern(
    container: Container,
    pattern: str,
    regex: bool = True
) -> bool:
    """Check if container logs contain a pattern.

    Args:
        container: Container object
        pattern: Pattern to search for (regex if regex=True, literal otherwise)
        regex: Whether pattern is a regex (default True)

    Returns:
        True if pattern found in logs, False otherwise
    """
    try:
        logs = container.logs(timestamps=False).decode('utf-8', errors='replace')
        if regex:
            return bool(re.search(pattern, logs))
        else:
            return pattern in logs
    except Exception as e:
        print_error(f"Error checking logs: {e}")
        return False


def print_next_steps(steps: List[str]) -> None:
    """Print a formatted next steps section.

    Args:
        steps: List of next step instructions
    """
    print()
    print(f"{Colors.BLUE}Next steps:{Colors.RESET}")
    for i, step in enumerate(steps, 1):
        print(f"  {i}. {step}")
    print()


def fail_with_message(message: str, suggestion: str = "") -> None:
    """Print error and exit.

    Args:
        message: Error message
        suggestion: Optional suggestion for fixing the error
    """
    print_error(message)
    if suggestion:
        print_info(suggestion)
    sys.exit(1)
