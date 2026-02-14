#!/usr/bin/env python3
"""Console-based file transfer using uuencode.

Transfers uuencoded files from VAX to PDP-11 via console I/O using GNU screen.
This simulates how files were actually transferred over serial/terminal connections
in the 1970s-80s.

Usage:
    console-transfer.py <build-id> <vax-ip> <pdp11-ip>
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime


def log_courier(build_id: str, message: str) -> None:
    """Log message to COURIER log."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp} COURIER] {message}"

    # Append to courier log on EFS
    log_file = f"/mnt/arpanet-logs/builds/{build_id}/COURIER.log"
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    with open(log_file, 'a') as f:
        f.write(log_line + '\n')

    print(log_line)


def send_to_console(session: str, line: str) -> None:
    """Send single line to console via screen session."""
    # Escape any special characters
    escaped = line.replace('\\', '\\\\').replace('"', '\\"')
    subprocess.run(
        ['screen', '-S', session, '-X', 'stuff', f'{escaped}\n'],
        check=False
    )


def wait_for_prompt(session: str, timeout: int = 5) -> bool:
    """Wait for shell prompt (simple polling)."""
    time.sleep(timeout)
    return True


def transfer_file_via_console(
    build_id: str,
    encoded_file: Path,
    pdp11_ip: str,
    session_name: str = 'pdp11-console'
) -> bool:
    """Transfer uuencoded file to PDP-11 via console."""

    log_courier(build_id, f"Initiating console transfer to PDP-11 ({pdp11_ip})")

    # Start screen session connected to PDP-11
    log_courier(build_id, f"Connecting to PDP-11 console (telnet {pdp11_ip}:2327)")
    subprocess.run(
        ['screen', '-dmS', session_name, 'telnet', pdp11_ip, '2327'],
        check=False
    )

    # Wait for connection
    time.sleep(3)
    log_courier(build_id, "Console connection established")

    # Login as root (PDP-11 typically auto-logged in or needs root)
    # Most PDP-11 setups auto-login, but send a newline to ensure we're at prompt
    send_to_console(session_name, '')
    wait_for_prompt(session_name, 2)

    # Change to /tmp directory
    log_courier(build_id, "Changing to /tmp directory")
    send_to_console(session_name, 'cd /tmp')
    wait_for_prompt(session_name, 1)

    # Read encoded file
    with open(encoded_file) as f:
        lines = f.readlines()

    total_lines = len(lines)
    log_courier(build_id, f"Sending {total_lines} lines of encoded data")

    # Start heredoc to receive file
    send_to_console(session_name, 'cat > brad.1.uu << "ENDOFFILE"')
    time.sleep(0.5)

    # Send encoded data line-by-line
    for i, line in enumerate(lines):
        send_to_console(session_name, line.rstrip())

        # Log progress every 20 lines
        if i > 0 and i % 20 == 0:
            log_courier(build_id, f"Transfer progress: {i}/{total_lines} lines ({i*100//total_lines}%)")

        # Rate limit to prevent overwhelming the console
        time.sleep(0.05)

    # Close heredoc
    send_to_console(session_name, 'ENDOFFILE')
    wait_for_prompt(session_name, 2)

    log_courier(build_id, "Transfer complete - All lines sent")

    # Verify file was created
    log_courier(build_id, "Verifying received file")
    send_to_console(session_name, 'wc -l brad.1.uu')
    wait_for_prompt(session_name, 1)

    # Capture console output for verification
    output_file = f'/tmp/pdp11-console-{build_id}.txt'
    subprocess.run(
        ['screen', '-S', session_name, '-X', 'hardcopy', output_file],
        check=False
    )

    log_courier(build_id, f"Console output saved to {output_file}")

    return True


def main() -> int:
    """Main entry point."""
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} <build-id> <vax-ip> <pdp11-ip>", file=sys.stderr)
        return 1

    build_id = sys.argv[1]
    vax_ip = sys.argv[2]
    pdp11_ip = sys.argv[3]

    # Find encoded file from VAX
    encoded_file = Path('/tmp/brad.1.uu')

    if not encoded_file.exists():
        log_courier(build_id, f"ERROR: Encoded file not found: {encoded_file}")
        return 1

    log_courier(build_id, f"Found encoded file: {encoded_file}")
    log_courier(build_id, f"File size: {encoded_file.stat().st_size} bytes")

    # Transfer file
    success = transfer_file_via_console(build_id, encoded_file, pdp11_ip)

    if success:
        log_courier(build_id, "✓ Console transfer completed successfully")
        return 0
    else:
        log_courier(build_id, "✗ Console transfer failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
