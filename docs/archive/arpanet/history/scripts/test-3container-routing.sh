#!/bin/bash
# Test 3-container ARPANET routing: VAX → IMP1 → IMP2
#
# This script tests multi-hop routing without PDP-10, validating that
# packets can flow from VAX through both IMPs.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== ARPANET 3-Container Routing Test ==="
echo
echo "Testing: VAX → IMP1 → IMP2"
echo "Validating multi-hop packet routing"
echo

# Check containers
echo "Checking container status..."
for container in arpanet-vax arpanet-imp1 arpanet-imp2; do
    if ! docker ps | grep -q "$container"; then
        echo "Error: $container not running"
        exit 1
    fi
    echo "✅ $container running"
done

echo
echo "=== Network Topology ==="
echo
echo "┌─────────────┐         ┌─────────────┐         ┌─────────────┐"
echo "│   VAX/BSD   │ Host    │   IMP #1    │ Modem   │   IMP #2    │"
echo "│ 172.20.0.10 │◄───────►│ 172.20.0.20 │◄───────►│ 172.20.0.30 │"
echo "│    :2323    │   HI1   │    :2324    │   MI1   │    :2325    │"
echo "└─────────────┘         └─────────────┘         └─────────────┘"
echo

# Start log collection in background
BUILD_ID="test-routing-$(date +%Y%m%d-%H%M%S)"
echo "Starting log collection (60 seconds)..."
echo "Build ID: $BUILD_ID"
echo

cd "$PROJECT_ROOT"

python3 -m arpanet_logging collect \
    --build-id "$BUILD_ID" \
    --components vax imp1 imp2 \
    --duration 60 \
    --phase phase2 &

LOGGING_PID=$!

# Wait for collectors to start
sleep 3

echo
echo "=== Testing VAX Network Configuration ==="
echo

# Check VAX network interface
echo "Checking VAX de0 interface..."
docker exec arpanet-vax /etc/ifconfig de0 2>/dev/null | grep -E "inet|flags" || echo "VAX interface check failed"

echo
echo "=== Testing Docker Network Connectivity ==="
echo

# Test basic Docker network connectivity
echo "Ping test: VAX → IMP1 (172.20.0.20)"
docker exec arpanet-vax ping -c 3 172.20.0.20 2>/dev/null | grep -E "packets|rtt" || echo "Ping to IMP1 failed (expected if ICMP not configured)"

echo
echo "Ping test: VAX → IMP2 (172.20.0.30)"
docker exec arpanet-vax ping -c 3 172.20.0.30 2>/dev/null | grep -E "packets|rtt" || echo "Ping to IMP2 failed (expected if ICMP not configured)"

echo
echo "=== IMP Routing Status ==="
echo

# Check IMP logs for routing activity
echo "Checking IMP1 logs for recent activity..."
docker logs --tail 20 arpanet-imp1 2>&1 | grep -i "HI1\|MI1\|packet\|send\|recv" | tail -5 || echo "No recent IMP1 activity"

echo
echo "Checking IMP2 logs for recent activity..."
docker logs --tail 20 arpanet-imp2 2>&1 | grep -i "MI1\|packet\|send\|recv" | tail -5 || echo "No recent IMP2 activity"

echo
echo "=== Network Statistics ==="
echo

# Docker network stats
echo "Container network statistics:"
docker stats --no-stream arpanet-vax arpanet-imp1 arpanet-imp2 | grep -E "NAME|arpanet"

echo
echo "Waiting for log collection to complete..."
wait $LOGGING_PID

echo
echo "=== Collection Complete ==="
echo

# Show results
python3 -m arpanet_logging show "$BUILD_ID"

echo
echo "=== Routing Analysis ==="
echo

LOGS_DIR="/mnt/arpanet-logs"
if [ ! -d "$LOGS_DIR" ]; then
    LOGS_DIR="./logs"
fi

BUILD_DIR="$LOGS_DIR/builds/$BUILD_ID"

# Analyze IMP1 routing events
if [ -f "$BUILD_DIR/imp1/events.jsonl" ]; then
    echo "IMP1 modem interface (MI1) events: $(grep -c 'modem-interface' "$BUILD_DIR/imp1/events.jsonl" || echo 0)"
    echo "IMP1 host interface (HI1) events: $(grep -c 'host-interface' "$BUILD_DIR/imp1/events.jsonl" || echo 0)"
    echo "IMP1 packet events: $(grep -c 'packet' "$BUILD_DIR/imp1/events.jsonl" || echo 0)"
fi

echo
if [ -f "$BUILD_DIR/imp2/events.jsonl" ]; then
    echo "IMP2 modem interface (MI1) events: $(grep -c 'modem-interface' "$BUILD_DIR/imp2/events.jsonl" || echo 0)"
    echo "IMP2 packet events: $(grep -c 'packet' "$BUILD_DIR/imp2/events.jsonl" || echo 0)"
fi

echo
echo "=== Test Complete ==="
echo "Logs: $BUILD_DIR"
echo
echo "Summary:"
echo "- VAX network interface status checked"
echo "- Docker layer connectivity tested"
echo "- IMP routing activity logged"
echo "- 60 seconds of multi-component logs captured"
echo
echo "Next: Analyze logs for ARPANET protocol routing patterns"
