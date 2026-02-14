#!/bin/sh
# VAX-side build and encode script
# Runs on VAX (4.3BSD) to compile bradman and encode output for transfer
#
# Usage: vax-build-and-encode.sh <build-id>

BUILD_ID="$1"

if [ -z "$BUILD_ID" ]; then
    echo "Error: BUILD_ID required"
    echo "Usage: $0 <build-id>"
    exit 1
fi

echo "=== VAX BUILD & ENCODE ===" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "Build ID: $BUILD_ID" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "Date: $(date)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

cd /tmp || exit 1

# Compile bradman
echo "Compiling bradman.c..." | /tmp/arpanet-log.sh VAX "$BUILD_ID"
cc -o bradman bradman.c 2>&1 | /tmp/arpanet-log.sh VAX "$BUILD_ID"

if [ ! -f bradman ]; then
    echo "ERROR: Compilation failed" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

echo "Compilation successful" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

# Generate manpage
echo "Generating manpage from resume.vax.yaml..." | /tmp/arpanet-log.sh VAX "$BUILD_ID"
./bradman -i resume.vax.yaml -o brad.1 2>&1 | /tmp/arpanet-log.sh VAX "$BUILD_ID"

if [ ! -f brad.1 ]; then
    echo "ERROR: Manpage generation failed" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

echo "Manpage generated successfully" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

# Encode for transfer
echo "Encoding output for console transfer..." | /tmp/arpanet-log.sh VAX "$BUILD_ID"
uuencode brad.1 brad.1 > brad.1.uu 2>&1 | /tmp/arpanet-log.sh VAX "$BUILD_ID"

if [ ! -f brad.1.uu ]; then
    echo "ERROR: uuencode failed" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

# Report statistics
FILE_SIZE=$(wc -c < brad.1)
ENCODED_SIZE=$(wc -c < brad.1.uu)
LINE_COUNT=$(wc -l < brad.1.uu)

echo "Encoding complete" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Original file: brad.1 ($FILE_SIZE bytes)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Encoded file: brad.1.uu ($ENCODED_SIZE bytes, $LINE_COUNT lines)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Overhead: $(expr $ENCODED_SIZE \* 100 / $FILE_SIZE - 100)%" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

echo "VAX build complete - Output ready for transfer" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
exit 0
