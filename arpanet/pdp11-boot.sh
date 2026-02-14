#!/bin/bash
# PDP-11 boot wrapper - automatically mounts /usr after boot
# This script starts SIMH, waits for boot, and sends mount command

set -e

echo "[PDP-11] Starting SIMH PDP-11 emulator..."

# Start SIMH in background with config
pdp11 pdp11.ini &
PDP_PID=$!

echo "[PDP-11] SIMH started with PID $PDP_PID"
echo "[PDP-11] Waiting for console to be ready..."

# Wait for console telnet to be available
sleep 5
MAX_RETRIES=20
RETRY=0
while ! timeout 1 bash -c 'echo > /dev/tcp/localhost/2327' 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "[PDP-11] WARNING: Console not ready after ${MAX_RETRIES} seconds"
        break
    fi
    sleep 1
done

echo "[PDP-11] Console is ready, waiting for BSD boot (25 seconds)..."
sleep 25

echo "[PDP-11] Sending mount /usr command via nc..."

# Use nc (netcat) instead of telnet for better control
(
    sleep 2
    echo "mount /usr"
    sleep 1
    echo "# Auto-mount complete"
    sleep 1
) | nc -w 3 localhost 2327 >/dev/null 2>&1 || true

echo "[PDP-11] Mount command sent"
echo "[PDP-11] PDP-11 is ready"
echo "[PDP-11] To manually verify: telnet localhost 2327"
echo "[PDP-11] Then run: mount (should show /dev/xp0e on /usr)"

# Wait for SIMH process to exit (keeps container running)
wait $PDP_PID
