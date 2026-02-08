#!/bin/bash
# Test IMP log collection and ARPANET protocol parsing
#
# This script tests the new IMP collectors by collecting logs from
# IMP1 and IMP2, parsing ARPANET 1822 protocol messages, and displaying
# tagged events.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== ARPANET IMP Log Collection Test ==="
echo
echo "Testing IMP collectors with ARPANET 1822 protocol parser"
echo "Project root: $PROJECT_ROOT"
echo

# Check if Docker containers are running
echo "Checking container status..."
if ! docker ps | grep -q arpanet-imp1; then
    echo "Error: arpanet-imp1 container not running"
    echo "Start with: docker compose -f docker-compose.arpanet.phase2.yml up -d"
    exit 1
fi

if ! docker ps | grep -q arpanet-imp2; then
    echo "Error: arpanet-imp2 container not running"
    echo "Start with: docker compose -f docker-compose.arpanet.phase2.yml up -d"
    exit 1
fi

echo "✅ Both IMP containers running"
echo

# Run log collection for 30 seconds
BUILD_ID="test-imp-$(date +%Y%m%d-%H%M%S)"
DURATION=30

echo "Collecting logs for ${DURATION} seconds..."
echo "Build ID: $BUILD_ID"
echo "Components: imp1, imp2"
echo

cd "$PROJECT_ROOT"

python3 -m arpanet_logging collect \
    --build-id "$BUILD_ID" \
    --components imp1 imp2 \
    --duration "$DURATION" \
    --phase phase2

echo
echo "=== Collection Complete ==="
echo

# Show results
echo "=== Build Summary ==="
python3 -m arpanet_logging show "$BUILD_ID"

echo
echo "=== Sample IMP1 Events ==="
echo "Showing first 10 tagged events from IMP1:"
echo

# Show sample events
LOGS_DIR="/mnt/arpanet-logs"
if [ ! -d "$LOGS_DIR" ]; then
    LOGS_DIR="./logs"
fi

BUILD_DIR="$LOGS_DIR/builds/$BUILD_ID"

if [ -f "$BUILD_DIR/imp1/events.jsonl" ]; then
    echo "IMP1 events (first 10):"
    head -10 "$BUILD_DIR/imp1/events.jsonl" | jq -r '.tags | join(", ")' | nl
    echo
    echo "Total IMP1 events: $(wc -l < "$BUILD_DIR/imp1/events.jsonl")"
fi

if [ -f "$BUILD_DIR/imp2/events.jsonl" ]; then
    echo
    echo "IMP2 events (first 10):"
    head -10 "$BUILD_DIR/imp2/events.jsonl" | jq -r '.tags | join(", ")' | nl
    echo
    echo "Total IMP2 events: $(wc -l < "$BUILD_DIR/imp2/events.jsonl")"
fi

echo
echo "=== Test Complete ==="
echo "Logs stored in: $BUILD_DIR"
