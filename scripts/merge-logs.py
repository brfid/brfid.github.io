#!/usr/bin/env python3
"""Merge timestamped logs chronologically from multiple machines.

Usage:
    python scripts/merge-logs.py <build-id> [base-path]

Reads all *.log files from <base-path>/builds/<build-id>/
and merges them chronologically into merged.log.

Default base path: /mnt/arpanet-logs

Log format: [YYYY-MM-DD HH:MM:SS MACHINE] message
"""

import re
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


def parse_log_line(line: str) -> Tuple[datetime, str] | None:
    """Parse a timestamped log line.

    Args:
        line: Log line in format "[YYYY-MM-DD HH:MM:SS MACHINE] message"

    Returns:
        Tuple of (timestamp, full_line) or None if parsing fails
    """
    # Match: [YYYY-MM-DD HH:MM:SS MACHINE] ...
    match = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \w+\]', line)
    if not match:
        return None

    try:
        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        return (timestamp, line.rstrip('\n'))
    except ValueError:
        return None


def merge_logs(build_dir: Path) -> List[str]:
    """Merge all *.log files in build_dir chronologically.

    Args:
        build_dir: Directory containing *.log files

    Returns:
        List of merged log lines sorted by timestamp
    """
    entries: List[Tuple[datetime, str]] = []

    # Read all .log files
    for log_file in sorted(build_dir.glob('*.log')):
        if log_file.name == 'merged.log':
            continue  # Skip the output file

        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parsed = parse_log_line(line)
                if parsed:
                    entries.append(parsed)

    # Sort by timestamp
    entries.sort(key=lambda x: x[0])

    # Return just the lines
    return [line for _, line in entries]


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(f"Usage: {sys.argv[0]} <build-id> [base-path]", file=sys.stderr)
        print(f"Default base path: /mnt/arpanet-logs", file=sys.stderr)
        return 1

    build_id = sys.argv[1]
    base_path = sys.argv[2] if len(sys.argv) == 3 else os.getenv('ARPANET_LOGS_BASE', '/mnt/arpanet-logs')
    build_dir = Path(base_path) / 'builds' / build_id

    if not build_dir.exists():
        print(f"Error: Build directory not found: {build_dir}", file=sys.stderr)
        return 1

    # Merge logs
    merged = merge_logs(build_dir)

    if not merged:
        print(f"Warning: No valid log entries found in {build_dir}", file=sys.stderr)
        return 1

    # Write merged output
    output_file = build_dir / 'merged.log'
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in merged:
            f.write(line + '\n')

    print(f"✅ Merged {len(merged)} log entries to: {output_file}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
