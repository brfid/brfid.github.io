#!/bin/bash
# Setup script for local ARPANET testing environment

set -e

echo "========================================="
echo "ARPANET Local Test Environment Setup"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi
echo "✅ Docker found: $(docker --version)"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi
echo "✅ Docker Compose found: $(docker compose version)"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "⚠️  Python 3 not found. Some test utilities may not work."
else
    echo "✅ Python 3 found: $(python3 --version)"
fi

# Check disk space
available=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$available" -lt 2 ]; then
    echo "⚠️  Low disk space: ${available}GB available (recommend 2GB+)"
else
    echo "✅ Disk space: ${available}GB available"
fi

echo ""
echo "Creating directories..."
mkdir -p ../../build/vax/simh-tape
mkdir -p ../../build/arpanet/imp1
echo "✅ Build directories created"

echo ""
echo "Pulling VAX base image (this may take a while)..."
docker pull jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215
echo "✅ VAX image ready"

echo ""
echo "========================================="
echo "Setup Complete"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Build IMP container:"
echo "     cd ../.."
echo "     docker compose -f docker-compose.arpanet.phase1.yml build"
echo ""
echo "  2. Run tests:"
echo "     make test"
echo ""
echo "  3. Or start network manually:"
echo "     docker compose -f docker-compose.arpanet.phase1.yml up -d"
echo ""
