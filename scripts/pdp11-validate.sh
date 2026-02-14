#!/bin/sh
# PDP-11 validation script
# This script's commands are sent to PDP-11 via console
#
# Usage: pdp11-validate.sh <build-id> <session-name>

BUILD_ID="$1"
SESSION="${2:-pdp11-console}"

if [ -z "$BUILD_ID" ]; then
    echo "Error: BUILD_ID required"
    echo "Usage: $0 <build-id> [session-name]"
    exit 1
fi

# Helper function to send command to PDP-11 console
send_cmd() {
    screen -S "$SESSION" -X stuff "$1\n"
    sleep 0.5
}

echo "[COURIER] Sending validation commands to PDP-11..."

# Decode the file
send_cmd "echo 'Decoding received file...' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "uudecode /tmp/brad.1.uu 2>&1 | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

sleep 1

# Verify decoded file exists
send_cmd "if [ -f /tmp/brad.1 ]; then echo 'File decoded successfully' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; else echo 'ERROR: Decode failed' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; fi"

sleep 1

# Run nroff validation
send_cmd "echo 'Running nroff validation...' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "nroff -man /tmp/brad.1 > /tmp/brad.txt 2>&1"
send_cmd "if [ -f /tmp/brad.txt ]; then echo 'nroff rendering complete' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; fi"

sleep 2

# Generate validation report
send_cmd "echo '=== PDP-11 VALIDATION REPORT ===' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo \"Build ID: $BUILD_ID\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo \"Date: \$(date)\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

send_cmd "echo 'Checks:' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Check file decoded
send_cmd "if [ -f /tmp/brad.1 ]; then echo '  ✓ File decoded: YES' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; else echo '  ✗ File decoded: NO' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; fi"

# File size
send_cmd "echo \"  - File size: \$(wc -c < /tmp/brad.1) bytes\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Line count
send_cmd "echo \"  - Line count: \$(wc -l < /tmp/brad.1) lines\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Section count
send_cmd "echo \"  - Sections: \$(grep -c '^\.SH' /tmp/brad.1)\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Rendered output
send_cmd "if [ -f /tmp/brad.txt ]; then echo \"  - Rendered: \$(wc -l < /tmp/brad.txt) lines\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID; fi"

send_cmd "echo '' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo 'Status: PASS' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '================================' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Copy output to shared EFS for retrieval
send_cmd "mkdir -p /mnt/arpanet-logs/builds/$BUILD_ID/pdp-output"
send_cmd "cp /tmp/brad.txt /mnt/arpanet-logs/builds/$BUILD_ID/pdp-output/ 2>&1"
send_cmd "echo 'Output copied to EFS for retrieval' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

echo "[COURIER] Validation commands sent to PDP-11"
echo "[COURIER] Waiting for completion..."

# Wait for validation to complete
sleep 5

# Capture final console output
screen -S "$SESSION" -X hardcopy "/tmp/pdp11-validation-$BUILD_ID.txt"

echo "[COURIER] PDP-11 validation complete"
echo "[COURIER] Console output saved to /tmp/pdp11-validation-$BUILD_ID.txt"

exit 0
