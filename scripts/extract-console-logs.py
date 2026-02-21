#!/usr/bin/env python3
"""Extract timestamped log entries from console captures.

Parses console output files (from screen hardcopy) and extracts
lines matching the arpanet-log format: [YYYY-MM-DD HH:MM:SS MACHINE] message

Usage:
    python scripts/extract-console-logs.py <console-file> <output-log> [machine-name]

Args:
    console-file: Screen hardcopy file (e.g., /tmp/vax-build-console.txt)
    output-log: Output log file (e.g., /mnt/arpanet-logs/builds/xyz/VAX.log)
    machine-name: Optional filter for specific machine (e.g., VAX, PDP11)

Examples:
    # Extract all VAX logs from console capture
    python scripts/extract-console-logs.py /tmp/vax-console.txt VAX.log VAX

    # Extract all logs (any machine)
    python scripts/extract-console-logs.py /tmp/console.txt all.log
"""

import re
import sys
from pathlib import Path
from typing import List, Optional


# Log format: [YYYY-MM-DD HH:MM:SS MACHINE] message
LOG_PATTERN = re.compile(
    r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+)\] (.+)$'
)


def extract_logs(
    console_file: Path,
    output_file: Path,
    machine_filter: Optional[str] = None
) -> int:
    """Extract timestamped log entries from console output.

    Args:
        console_file: Path to screen hardcopy file
        output_file: Path to output log file
        machine_filter: Optional machine name filter (e.g., 'VAX', 'PDP11')

    Returns:
        Number of log entries extracted
    """
    if not console_file.exists():
        print(f"Error: Console file not found: {console_file}", file=sys.stderr)
        return 0

    extracted = []

    with open(console_file, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n\r')
            match = LOG_PATTERN.match(line)

            if match:
                timestamp, machine, message = match.groups()

                # Filter by machine if specified
                if machine_filter and machine != machine_filter:
                    continue

                # Reconstruct log entry
                log_entry = f"[{timestamp} {machine}] {message}"
                extracted.append(log_entry)

    if not extracted:
        print(
            f"Warning: No log entries found in {console_file}",
            file=sys.stderr
        )
        return 0

    # Write to output file
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in extracted:
            f.write(entry + '\n')

    return len(extracted)


def main() -> int:
    """Main entry point."""
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    console_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    machine_filter = sys.argv[3] if len(sys.argv) > 3 else None

    count = extract_logs(console_file, output_file, machine_filter)

    if count > 0:
        print(f"✅ Extracted {count} log entries to {output_file}")
        if machine_filter:
            print(f"   Filtered by machine: {machine_filter}")
        return 0
    else:
        print(f"❌ No log entries extracted", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
