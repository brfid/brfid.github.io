#!/bin/bash
# PDP-11 boot wrapper - automatically mounts /usr after boot
# This script starts SIMH, waits for boot, and sends mount command

set -e

echo "[PDP-11] Starting SIMH PDP-11 emulator..."

# Start SIMH in background with config
pdp11 pdp11.ini &
PDP_PID=$!

echo "[PDP-11] SIMH started with PID $PDP_PID"
echo "[PDP-11] Waiting for BSD to boot (20 seconds)..."

# Wait for boot to complete
sleep 20

echo "[PDP-11] Boot should be complete, sending mount /usr command..."

# Connect to console and send mount command
# Console is on localhost:2327 (telnet)
(
    echo ""
    sleep 1
    echo "mount /usr"
    sleep 2
    echo "echo '[AUTO-MOUNT] /usr mounted successfully'"
    sleep 1
) | telnet localhost 2327 >/dev/null 2>&1 &

echo "[PDP-11] Mount command sent"
echo "[PDP-11] PDP-11 is ready"

# Wait for SIMH process to exit (keeps container running)
wait $PDP_PID
