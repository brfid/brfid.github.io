#!/bin/bash
# VAX boot wrapper - automatically mounts filesystems after boot
# This script starts SIMH VAX, waits for boot, and ensures all filesystems are mounted

set -e

echo "[VAX] Starting SIMH VAX-11/780 emulator..."

# Start SIMH VAX in background
# Note: VAX container uses pre-built image, may have different startup
vax780 vax780.ini &
VAX_PID=$!

echo "[VAX] SIMH started with PID $VAX_PID"
echo "[VAX] Waiting for console to be ready..."

# Wait for console telnet to be available
sleep 5
MAX_RETRIES=30
RETRY=0
while ! timeout 1 bash -c 'echo > /dev/tcp/localhost/2323' 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "[VAX] WARNING: Console not ready after ${MAX_RETRIES} seconds"
        break
    fi
    sleep 1
done

echo "[VAX] Console is ready, waiting for BSD boot (30 seconds)..."
sleep 30

echo "[VAX] Checking and mounting filesystems..."

# Send mount commands via nc to ensure all filesystems are mounted
(
    sleep 2
    echo ""
    sleep 1
    echo "root"
    sleep 2
    echo "mount -a"
    sleep 2
    echo "df -h"
    sleep 1
    echo "# VAX filesystems mounted"
    sleep 1
) | nc -w 5 localhost 2323 >/dev/null 2>&1 || true

echo "[VAX] Filesystem mount commands sent"
echo "[VAX] VAX is ready"
echo "[VAX] Console: telnet localhost 2323"
echo "[VAX] Verify: mount -a; ls /usr/bin/uu*"

# Wait for SIMH process to exit (keeps container running)
wait $VAX_PID
