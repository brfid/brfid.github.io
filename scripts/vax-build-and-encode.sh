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
echo "  Compiler: cc (4.3BSD K&R C)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Source: bradman.c ($(wc -l < bradman.c) lines)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

COMPILE_OUTPUT=$(cc -o bradman bradman.c 2>&1)
COMPILE_STATUS=$?

if [ $COMPILE_STATUS -ne 0 ]; then
    echo "ERROR: Compilation failed with status $COMPILE_STATUS" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    echo "$COMPILE_OUTPUT" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

if [ ! -f bradman ]; then
    echo "ERROR: Compilation failed - binary not created" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

BINARY_SIZE=$(wc -c < bradman)
echo "Compilation successful" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Binary size: $BINARY_SIZE bytes" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
if [ -n "$COMPILE_OUTPUT" ]; then
    echo "  Compiler warnings:" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    echo "$COMPILE_OUTPUT" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
fi

# Generate manpage
echo "Generating manpage from resume.vax.yaml..." | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Input: resume.vax.yaml ($(wc -l < resume.vax.yaml) lines)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Parser: bradman (VAX C YAML parser)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

MANPAGE_OUTPUT=$(./bradman -i resume.vax.yaml -o brad.1 2>&1)
MANPAGE_STATUS=$?

if [ $MANPAGE_STATUS -ne 0 ]; then
    echo "ERROR: Manpage generation failed with status $MANPAGE_STATUS" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    echo "$MANPAGE_OUTPUT" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

if [ ! -f brad.1 ]; then
    echo "ERROR: Manpage generation failed - output not created" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
    exit 1
fi

MANPAGE_SIZE=$(wc -c < brad.1)
MANPAGE_LINES=$(wc -l < brad.1)
SECTION_COUNT=$(grep -c '^\.SH' brad.1 || echo 0)

echo "Manpage generated successfully" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Output: brad.1 ($MANPAGE_SIZE bytes, $MANPAGE_LINES lines)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Sections: $SECTION_COUNT (.SH directives)" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
echo "  Format: troff/nroff man(7) macros" | /tmp/arpanet-log.sh VAX "$BUILD_ID"

# Show first section as sample
echo "  Sample (first 3 lines):" | /tmp/arpanet-log.sh VAX "$BUILD_ID"
head -3 brad.1 | sed 's/^/    /' | /tmp/arpanet-log.sh VAX "$BUILD_ID"

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
