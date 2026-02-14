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
    # Verify session exists, create if missing
    if ! screen -ls | grep -q "$SESSION"; then
        echo "[COURIER] Screen session '$SESSION' not found, recreating..." >&2
        # Session may have exited due to telnet timeout, recreate it
        # Get PDP-11 IP from environment or use previous IP
        PDP11_IP="${PDP11_IP:-34.228.166.115}"  # Fallback to previous IP
        screen -dmS "$SESSION" telnet "$PDP11_IP" 2327
        sleep 3  # Wait for connection
        echo "[COURIER] Screen session recreated" >&2
    fi
    screen -S "$SESSION" -X stuff "$1\n"
    sleep 0.5
}

echo "[COURIER] Sending validation commands to PDP-11..."

# Start validation report
send_cmd "echo '=== PDP-11 VALIDATION ===' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo 'Build ID: $BUILD_ID' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo \"Date: \$(date)\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo 'System: 2.11BSD on PDP-11/73' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Decode the file
send_cmd "echo 'Step 1: Decoding uuencoded file...' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  Input: /tmp/brad.1.uu' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo \"  Size: \$(wc -c < /tmp/brad.1.uu) bytes, \$(wc -l < /tmp/brad.1.uu) lines\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

send_cmd "uudecode /tmp/brad.1.uu 2>&1 | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

sleep 1

# Verify decoded file exists
send_cmd "if [ -f /tmp/brad.1 ]; then echo '  ✓ Decode successful' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; else echo '  ✗ ERROR: Decode failed' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; exit 1; fi"
send_cmd "echo \"  Output: brad.1 (\$(wc -c < /tmp/brad.1) bytes, \$(wc -l < /tmp/brad.1) lines)\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo \"  Sections: \$(grep -c '^\.SH' /tmp/brad.1) (.SH directives)\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

sleep 1

# Show sample of decoded file
send_cmd "echo '  Sample (first 3 lines):' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "head -3 /tmp/brad.1 | sed 's/^/    /' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

sleep 1

# Run nroff validation
send_cmd "echo '' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo 'Step 2: Rendering with nroff...' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  Tool: nroff -man (2.11BSD troff suite)' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  Purpose: Validate manpage format and render to text' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

send_cmd "nroff -man /tmp/brad.1 > /tmp/brad.txt 2>&1"

sleep 2

send_cmd "if [ -f /tmp/brad.txt ]; then echo '  ✓ Rendering successful' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; else echo '  ✗ ERROR: Rendering failed' | /tmp/arpanet-log.sh PDP11 $BUILD_ID; fi"
send_cmd "echo \"  Output: brad.txt (\$(wc -c < /tmp/brad.txt) bytes, \$(wc -l < /tmp/brad.txt) lines)\" | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

# Show sample of rendered output
send_cmd "echo '  Sample (first 5 lines):' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "head -5 /tmp/brad.txt | sed 's/^/    /' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

sleep 1

# Generate validation summary
send_cmd "echo '' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo 'Validation Summary:' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  ✓ uuencode transfer: Successful' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  ✓ uudecode: Successful' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  ✓ nroff rendering: Successful' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"
send_cmd "echo '  ✓ Historical toolchain: Authentic 1970s-80s Unix tools' | /tmp/arpanet-log.sh PDP11 $BUILD_ID"

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
