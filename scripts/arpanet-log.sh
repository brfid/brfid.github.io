#!/bin/sh
# DRY logging system for VAX and PDP-11
# Usage: command | arpanet-log <machine-name> <build-id>
#
# Captures all input with timestamps and writes to EFS build log
# Example: cc -o bradman bradman.c 2>&1 | arpanet-log VAX 2026-02-13-22-45-12-abc123

MACHINE="$1"
BUILD_ID="$2"
LOG_DIR="/mnt/arpanet-logs/builds/$BUILD_ID"
LOG_FILE="$LOG_DIR/${MACHINE}.log"

# Create build directory if it doesn't exist (may fail if EFS not accessible from BSD)
mkdir -p "$LOG_DIR" 2>/dev/null || true

# Fallback to /tmp if EFS not accessible
if [ ! -d "$LOG_DIR" ]; then
    LOG_DIR="/tmp/arpanet-logs-$BUILD_ID"
    LOG_FILE="$LOG_DIR/${MACHINE}.log"
    mkdir -p "$LOG_DIR"
fi

# Read stdin and timestamp each line
while IFS= read -r line; do
    # BSD date doesn't have %3N, so we use %S for seconds
    timestamp=$(date -u '+%Y-%m-%d %H:%M:%S')
    # Write to log file and echo to stdout for visibility
    echo "[$timestamp $MACHINE] $line" >> "$LOG_FILE"
    echo "[$timestamp $MACHINE] $line"
done
