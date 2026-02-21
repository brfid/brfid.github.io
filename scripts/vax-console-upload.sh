#!/bin/bash
# VAX Console File Uploader
# Sends files to VAX BSD via console using heredoc method
#
# Usage: vax-console-upload.sh <file> <destination>
#   e.g., vax-console-upload.sh vintage/machines/vax/bradman.c /tmp/bradman.c

set -e

FILE="$1"
DEST="$2"
VAX_IP="${3:-172.20.0.10}"

if [ -z "$FILE" ] || [ -z "$DEST" ]; then
    echo "Usage: $0 <file> <destination> [vax-ip]"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "Error: File not found: $FILE"
    exit 1
fi

SESSION="vax-upload-$$"
LINES=$(wc -l < "$FILE")
echo "[UPLOAD] Starting upload of $FILE ($LINES lines) to VAX:$DEST"

# Create screen session
echo "[UPLOAD] Creating screen session..."
screen -dmS "$SESSION" telnet "$VAX_IP" 2323
sleep 4

# Helper to send commands
send_cmd() {
    screen -S "$SESSION" -X stuff "$1\n"
    sleep "${2:-1}"
}

# Login
send_cmd "" 0.5
send_cmd "root" 2

# Change to destination directory
DEST_DIR=$(dirname "$DEST")
send_cmd "cd $DEST_DIR" 1

# Start heredoc
FILENAME=$(basename "$DEST")
echo "[UPLOAD] Sending file via heredoc..."
send_cmd "cat > $FILENAME << \"UPLOAD_EOF\"" 0.5

# Send file line by line
LINE_NUM=0
while IFS= read -r line; do
    LINE_NUM=$((LINE_NUM + 1))
    screen -S "$SESSION" -X stuff "$line\r"
    
    # Progress every 100 lines
    if [ $((LINE_NUM % 100)) -eq 0 ]; then
        echo "[UPLOAD] Sent $LINE_NUM / $LINES lines..."
    fi
    
    # Small delay to prevent buffer overflow
    sleep 0.02
done < "$FILE"

# Close heredoc
send_cmd "UPLOAD_EOF" 2

# Verify
send_cmd "ls -la $FILENAME" 1
send_cmd "wc -l $FILENAME" 1

echo "[UPLOAD] Upload complete!"
echo "[UPLOAD] Sent $LINE_NUM lines"

# Cleanup
screen -S "$SESSION" -X quit 2>/dev/null || true

echo "[UPLOAD] Done!"
