"""Docker operations for ARPANET testing.

Utility functions for interacting with Docker and Docker Compose.
"""

import subprocess
from pathlib import Path
from typing import Optional


def check_docker_available() -> bool:
    """Check if Docker is available and running.

    Returns:
        True if Docker is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ['docker', 'info'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def compose_build(compose_file: Path, verbose: bool = False) -> bool:
    """Build containers using Docker Compose.

    Args:
        compose_file: Path to docker-compose.yml file.
        verbose: Show build output.

    Returns:
        True if build succeeds, False otherwise.
    """
    cmd = [
        'docker', 'compose',
        '-f', str(compose_file),
        'build'
    ]

    if verbose:
        cmd.append('--progress=plain')

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None,
            timeout=600,  # 10 minute timeout
            cwd=compose_file.parent
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Build timed out after 10 minutes")
        return False


def compose_up(compose_file: Path, verbose: bool = False) -> bool:
    """Start containers using Docker Compose.

    Args:
        compose_file: Path to docker-compose.yml file.
        verbose: Show startup output.

    Returns:
        True if startup succeeds, False otherwise.
    """
    cmd = [
        'docker', 'compose',
        '-f', str(compose_file),
        'up', '-d'
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None,
            timeout=120,
            cwd=compose_file.parent
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Startup timed out after 2 minutes")
        return False


def compose_down(compose_file: Path, volumes: bool = True) -> bool:
    """Stop and remove containers using Docker Compose.

    Args:
        compose_file: Path to docker-compose.yml file.
        volumes: Also remove volumes.

    Returns:
        True if cleanup succeeds, False otherwise.
    """
    cmd = [
        'docker', 'compose',
        '-f', str(compose_file),
        'down'
    ]

    if volumes:
        cmd.append('-v')

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            cwd=compose_file.parent
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Cleanup timed out after 1 minute")
        return False


def container_is_running(container_name: str) -> bool:
    """Check if a container is running.

    Args:
        container_name: Name of container to check.

    Returns:
        True if container is running, False otherwise.
    """
    try:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            text=True
        )
        return container_name in result.stdout
    except subprocess.TimeoutExpired:
        return False


def get_container_logs(container_name: str, tail: Optional[int] = None) -> str:
    """Get logs from a container.

    Args:
        container_name: Name of container.
        tail: Number of lines to retrieve (None for all).

    Returns:
        Container logs as string.
    """
    cmd = ['docker', 'logs', container_name]

    if tail:
        cmd.extend(['--tail', str(tail)])

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
            text=True
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Failed to retrieve logs (timeout)"
