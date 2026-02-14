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

# Create build directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Read stdin and timestamp each line
while IFS= read -r line; do
    # BSD date doesn't have %3N, so we use %S for seconds
    timestamp=$(date -u '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp $MACHINE] $line" >> "$LOG_FILE"
done

# If running interactively (tty), also echo to stdout
if [ -t 1 ]; then
    tee -a "$LOG_FILE"
else
    cat >> "$LOG_FILE"
fi
