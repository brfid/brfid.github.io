"""Log parsing utilities for SIMH and IMP logs.

Functions for parsing and analyzing container logs to verify
proper initialization and detect errors.
"""

import re
from typing import Dict, List, Optional


def parse_vax_logs(logs: str) -> Dict[str, Optional[str]]:
    """Parse VAX container logs for key information.

    Args:
        logs: Raw log output from VAX container.

    Returns:
        Dictionary with parsed information:
        - 'boot_started': Whether boot sequence started
        - 'simh_version': SIMH version string
        - 'cpu_type': CPU type (e.g., 'VAX 780')
    """
    info = {
        'boot_started': False,
        'simh_version': None,
        'cpu_type': None,
    }

    # Check for SIMH version
    version_match = re.search(r'VAX simulator ([^\n]+)', logs)
    if version_match:
        info['simh_version'] = version_match.group(1)

    # Check for CPU type
    cpu_match = re.search(r'(VAX \d+)', logs)
    if cpu_match:
        info['cpu_type'] = cpu_match.group(1)

    # Check for boot sequence
    if 'Booting' in logs or 'boot' in logs.lower():
        info['boot_started'] = True

    return info


def parse_imp_logs(logs: str) -> Dict[str, Optional[str]]:
    """Parse IMP container logs for key information.

    Args:
        logs: Raw log output from IMP container.

    Returns:
        Dictionary with parsed information:
        - 'firmware_loaded': Whether IMP firmware loaded
        - 'simh_version': SIMH version string
        - 'imp_number': IMP number if configured
    """
    info = {
        'firmware_loaded': False,
        'simh_version': None,
        'imp_number': None,
    }

    # Check for SIMH version
    version_match = re.search(r'H316 simulator ([^\n]+)', logs)
    if version_match:
        info['simh_version'] = version_match.group(1)

    # Check for IMP number
    imp_match = re.search(r'IMP.*?(\d+)', logs)
    if imp_match:
        info['imp_number'] = imp_match.group(1)

    # Check for firmware load
    if 'impcode' in logs.lower() or 'firmware' in logs.lower():
        info['firmware_loaded'] = True

    return info


def check_for_errors(logs: str) -> List[str]:
    """Check logs for common error patterns.

    Args:
        logs: Raw log output.

    Returns:
        List of error messages found.
    """
    errors = []

    # Common error patterns
    error_patterns = [
        r'Error:? (.+)',
        r'ERROR:? (.+)',
        r'FATAL:? (.+)',
        r'Cannot (.+)',
        r'Failed to (.+)',
        r'not found',
        r'No such file',
    ]

    for pattern in error_patterns:
        matches = re.findall(pattern, logs, re.IGNORECASE)
        errors.extend(matches)

    # Filter out common false positives
    filtered_errors = []
    for error in errors:
        # Skip if it's just a warning or info message
        if 'warning' in error.lower():
            continue
        if 'info' in error.lower():
            continue
        filtered_errors.append(error)

    return filtered_errors


def extract_network_info(logs: str) -> Dict[str, Optional[str]]:
    """Extract network configuration from logs.

    Args:
        logs: Raw log output.

    Returns:
        Dictionary with network information:
        - 'ip_address': Configured IP address
        - 'network': Network name
        - 'ports': List of exposed ports
    """
    info = {
        'ip_address': None,
        'network': None,
        'ports': [],
    }

    # Extract IP address
    ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', logs)
    if ip_match:
        info['ip_address'] = ip_match.group(1)

    # Extract network name
    network_match = re.search(r'network.*?([a-z0-9-]+)', logs, re.IGNORECASE)
    if network_match:
        info['network'] = network_match.group(1)

    # Extract ports
    port_matches = re.findall(r'port.*?(\d{4,5})', logs, re.IGNORECASE)
    info['ports'] = list(set(port_matches))  # Deduplicate

    return info
