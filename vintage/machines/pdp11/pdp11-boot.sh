#!/bin/bash
# PDP-11 boot wrapper - handles 2.11BSD boot sequence via console
#
# Boot sequence:
#   1. SIMH starts and opens telnet console on 2327 immediately
#   2. Disk boot ROM runs and waits at 2.11BSD "Boot:" prompt (shown as ":")
#   3. Operator/automation connects via telnet and presses Enter to boot default
#      kernel (unix, not netnix)
#
# IMPORTANT:
# Avoid one-shot nc/telnet injections in this wrapper. Disconnecting the console
# during early boot has caused SIMH TTI disconnect errors and reboot loops.
# Console orchestration is handled by pipeline scripts using persistent screen
# sessions.

set -e

echo "[PDP-11] Starting SIMH PDP-11 emulator..."

# Start SIMH in background with config
pdp11 pdp11.ini &
PDP_PID=$!

echo "[PDP-11] SIMH started with PID $PDP_PID"
echo "[PDP-11] Allowing SIMH to initialize console listener..."

# IMPORTANT: do not probe localhost:2327 from this wrapper.
# A one-shot connect/disconnect during early boot can trigger SIMH TTI
# disconnect handling and reboot loops.
sleep 2

if ! kill -0 "$PDP_PID" 2>/dev/null; then
    echo "[PDP-11] ERROR: SIMH exited before console initialization completed"
    exit 1
fi

echo "[PDP-11] SIMH should now be listening on console port 2327"

# Start auto-boot handler: connects to the console, sends Enter at Boot:,
# waits for multi-user login: prompt, then disconnects cleanly.
# This prevents SIMH from timing out when no external client connects.
/opt/pdp11/auto-boot.exp 2>&1 &
echo "[PDP-11] Auto-boot handler started (PID $!)"
echo "[PDP-11] Port 2327 will be free for external clients once login: appears"

# Keep container alive
wait $PDP_PID

