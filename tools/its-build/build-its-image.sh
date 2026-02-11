#!/usr/bin/env bash
# Build ITS disk image using Docker on Mac M2 (x86_64 via Rosetta)
# Output: artifacts/ directory with KLH10 config + RP06 disk image
#
# Prerequisites:
#   - Docker Desktop with Rosetta enabled (Settings > General > Use Rosetta)
#   - Or: any x86_64 Linux host
#
# Usage: ./build-its-image.sh [--extract-to DIR]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT_TO="${1:-$SCRIPT_DIR/artifacts}"

echo "=== Building ITS disk image (x86_64 container) ==="
echo "This will take 10-30 minutes on first run."
echo ""

# Build the Docker image
docker build \
    --platform linux/amd64 \
    -t its-builder:latest \
    "$SCRIPT_DIR"

# Extract artifacts
mkdir -p "$EXTRACT_TO"

echo "=== Extracting artifacts to $EXTRACT_TO ==="

# Run container and copy out the artifacts
CONTAINER_ID=$(docker create --platform linux/amd64 its-builder:latest)
docker cp "$CONTAINER_ID:/artifacts/." "$EXTRACT_TO/" 2>/dev/null || {
    echo "WARNING: /artifacts copy failed, trying alternate paths..."
    # The ITS build system output location may vary
    docker cp "$CONTAINER_ID:/build/its/out/." "$EXTRACT_TO/" 2>/dev/null || true
}
docker rm "$CONTAINER_ID"

echo ""
echo "=== Build complete ==="
echo "Artifacts in: $EXTRACT_TO"
ls -la "$EXTRACT_TO"
echo ""
echo "Next steps:"
echo "  1. Copy artifacts to Pi:  scp -r $EXTRACT_TO pi@<pi-host>:~/its/"
echo "  2. On Pi, run:            cd ~/its && ./run-its-on-pi.sh"
echo "  (See tools/its-build/run-its-on-pi.sh)"
