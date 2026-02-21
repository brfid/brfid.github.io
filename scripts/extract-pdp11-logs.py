#!/usr/bin/env python3
"""
Extract PDP-11 logs from console capture

Filters console output to extract only PDP11-tagged log lines.
Used by GitHub Actions workflow to process console captures.

Usage:
    python3 extract-pdp11-logs.py <input_file> <output_file>
"""

import re
import sys

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <input_file> <output_file>", file=sys.stderr)
    sys.exit(1)

input_file = sys.argv[1]
output_file = sys.argv[2]

pattern = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+)\] (.+)$')

with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        match = pattern.match(line.rstrip())
        if match and match.group(2) == 'PDP11':
            outfile.write(line)

print('PDP-11 logs extracted')
