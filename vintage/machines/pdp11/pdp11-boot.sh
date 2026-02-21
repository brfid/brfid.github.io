#!/bin/bash
# PDP-11 boot wrapper - handles 2.11BSD boot sequence via console
#
# Boot sequence:
#   1. SIMH starts and opens telnet console on 2327 immediately
#   2. Disk boot ROM runs and shows 2.11BSD "Boot:" prompt (shown as ":")
#   3. We send Enter to select default kernel (unix, not netnix)
#   4. 2.11BSD boots to multi-user (~35-50 s in SIMH at full speed)
#   5. We send "mount /usr" to ensure /usr is mounted

set -e

echo "[PDP-11] Starting SIMH PDP-11 emulator..."

# Start SIMH in background with config
pdp11 pdp11.ini &
PDP_PID=$!

echo "[PDP-11] SIMH started with PID $PDP_PID"
echo "[PDP-11] Waiting for telnet console (port 2327) to open..."

# Wait for SIMH to open the console telnet port
MAX_RETRIES=30
RETRY=0
while ! timeout 1 bash -c 'echo > /dev/tcp/localhost/2327' 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "[PDP-11] ERROR: Console port 2327 not ready after ${MAX_RETRIES}s"
        exit 1
    fi
    sleep 1
done
echo "[PDP-11] Console port 2327 is open"

# SIMH opens 2327 before the disk boot ROM runs.  Give the boot ROM a few
# seconds to load from the RP06 image and display the "Boot:" (":") prompt.
echo "[PDP-11] Waiting 5s for disk boot ROM to display Boot: prompt..."
sleep 5

# Send Enter to accept the default kernel (unix).
# The 2.11BSD standalone boot boots "unix" when you press Enter at ":".
echo "[PDP-11] Sending Enter at Boot: prompt to select default kernel..."
printf "\r\n" | nc -w 2 localhost 2327 >/dev/null 2>&1 || true
echo "[PDP-11] Boot: prompt acknowledged"

# Wait for 2.11BSD to reach multi-user.  At full SIMH speed this takes
# roughly 35-50 seconds for the rpethset image.
echo "[PDP-11] Waiting 50s for 2.11BSD to reach multi-user..."
sleep 50

# Send mount /usr in case the plain unix kernel left it unmounted.
echo "[PDP-11] Sending 'mount /usr' via console..."
(
    sleep 1
    printf "mount /usr\r\n"
    sleep 2
) | nc -w 5 localhost 2327 >/dev/null 2>&1 || true
echo "[PDP-11] Startup sequence complete"
echo "[PDP-11] To verify: telnet localhost 2327"
echo "[PDP-11]   then: mount  (should show /dev/xp0e on /usr)"
echo "[PDP-11]   then: ls /usr/bin/uudecode /usr/bin/nroff"

# Keep container alive
wait $PDP_PID

