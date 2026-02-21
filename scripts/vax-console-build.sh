#!/bin/bash
# VAX console-based build executor
# Sends build commands to VAX BSD console instead of running in container
#
# Usage: vax-console-build.sh <build-id> <vax-ip>

set -e

BUILD_ID="$1"
VAX_IP="$2"

if [ -z "$BUILD_ID" ] || [ -z "$VAX_IP" ]; then
    echo "Usage: $0 <build-id> <vax-ip>"
    exit 1
fi

SESSION="vax-build-$$"

echo "[VAX-CONSOLE] Starting VAX build via console (Build: $BUILD_ID)"
echo "[VAX-CONSOLE] VAX IP: $VAX_IP"
echo "[VAX-CONSOLE] Session: $SESSION"

# Create screen session connected to VAX console
echo "[VAX-CONSOLE] Connecting to VAX console..."
screen -dmS "$SESSION" telnet "$VAX_IP" 2323
sleep 3

# Helper to send commands
send_cmd() {
    screen -S "$SESSION" -X stuff "$1\n"
    sleep "${2:-1}"
}

# Login (may already be logged in)
send_cmd "" 0.5
send_cmd "root" 2

# Change to /tmp where files are accessible
send_cmd "cd /tmp" 1

# Read the build script and send commands line by line
# This simulates running the script inside BSD
echo "[VAX-CONSOLE] Sending build commands to BSD..."

# Start logging
send_cmd "echo '=== VAX BUILD & ENCODE ===' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo 'Build ID: $BUILD_ID' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo \"Date: \$(date)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

# Compile bradman
send_cmd "echo 'Compiling bradman.c...' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo '  Compiler: cc (4.3BSD K&R C)' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo \"  Source: bradman.c (\$(wc -l < bradman.c) lines)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

send_cmd "cc -o bradman bradman.c 2>&1 | /tmp/arpanet-log.sh VAX $BUILD_ID" 3

send_cmd "if [ -f bradman ]; then echo 'Compilation successful' | /tmp/arpanet-log.sh VAX $BUILD_ID; else echo 'ERROR: Compilation failed' | /tmp/arpanet-log.sh VAX $BUILD_ID; exit 1; fi" 2

send_cmd "echo \"  Binary size: \$(wc -c < bradman) bytes\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

# Generate manpage
send_cmd "echo 'Generating manpage from resume.vax.yaml...' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo \"  Input: resume.vax.yaml (\$(wc -l < resume.vax.yaml) lines)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo '  Parser: bradman (VAX C YAML parser)' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

send_cmd "./bradman -i resume.vax.yaml -o brad.1 2>&1 | /tmp/arpanet-log.sh VAX $BUILD_ID" 2

send_cmd "if [ -f brad.1 ]; then echo 'Manpage generated successfully' | /tmp/arpanet-log.sh VAX $BUILD_ID; else echo 'ERROR: Manpage generation failed' | /tmp/arpanet-log.sh VAX $BUILD_ID; exit 1; fi" 2

send_cmd "echo \"  Output: brad.1 (\$(wc -c < brad.1) bytes, \$(wc -l < brad.1) lines)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo \"  Sections: \$(grep -c '^\\.SH' brad.1) (.SH directives)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo '  Format: troff/nroff man(7) macros' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

# Show sample
send_cmd "echo '  Sample (first 3 lines):' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "head -3 brad.1 | sed 's/^/    /' | /tmp/arpanet-log.sh VAX $BUILD_ID" 2

# Encode for transfer
send_cmd "echo 'Encoding output for console transfer...' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "uuencode brad.1 brad.1 > brad.1.uu 2>&1" 2

send_cmd "if [ -f brad.1.uu ]; then echo 'Encoding complete' | /tmp/arpanet-log.sh VAX $BUILD_ID; else echo 'ERROR: uuencode failed' | /tmp/arpanet-log.sh VAX $BUILD_ID; exit 1; fi" 2

send_cmd "FILE_SIZE=\$(wc -c < brad.1)" 1
send_cmd "ENCODED_SIZE=\$(wc -c < brad.1.uu)" 1
send_cmd "LINE_COUNT=\$(wc -l < brad.1.uu)" 1

send_cmd "echo \"  Original file: brad.1 (\$FILE_SIZE bytes)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1
send_cmd "echo \"  Encoded file: brad.1.uu (\$ENCODED_SIZE bytes, \$LINE_COUNT lines)\" | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

# Copy encoded file to /machines/data for retrieval
send_cmd "cp brad.1.uu /machines/data/" 1

send_cmd "echo 'VAX build complete - Output ready for transfer' | /tmp/arpanet-log.sh VAX $BUILD_ID" 1

echo "[VAX-CONSOLE] Build commands sent"
echo "[VAX-CONSOLE] Waiting for completion (10 seconds)..."
sleep 10

# Capture console output
screen -S "$SESSION" -X hardcopy "/tmp/vax-console-$BUILD_ID.txt"

echo "[VAX-CONSOLE] Console output saved to /tmp/vax-console-$BUILD_ID.txt"
echo "[VAX-CONSOLE] Build complete"

# Cleanup screen session
screen -S "$SESSION" -X quit 2>/dev/null || true

exit 0
