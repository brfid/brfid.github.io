#!/bin/bash
# AWS Panda PDP-10 Testing Script
# Run this on the AWS instance to test VAX + PDP-10 connectivity

set -e

echo "=========================================="
echo "Panda PDP-10 AWS Testing Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on AWS
if [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "${YELLOW}Warning: SSH key not found. Make sure you're on the AWS instance.${NC}"
fi

echo "Step 1: Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found${NC}"
    exit 1
fi
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: Docker Compose not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker available${NC}"

echo ""
echo "Step 2: Navigating to project..."
cd ~/brfid.github.io || {
    echo -e "${RED}ERROR: Project directory not found${NC}"
    exit 1
}
echo -e "${GREEN}✓ In project directory${NC}"

echo ""
echo "Step 3: Building Panda PDP-10 container..."
echo "(This will download ~221MB and extract panda.rp)"
docker-compose -f docker-compose.panda-vax.yml build pdp10-panda
echo -e "${GREEN}✓ Build complete${NC}"

echo ""
echo "Step 4: Starting services..."
docker-compose -f docker-compose.panda-vax.yml up -d
echo -e "${GREEN}✓ Services started${NC}"

echo ""
echo "Step 5: Waiting for boot (~30 seconds)..."
sleep 30

echo ""
echo "Step 6: Checking container status..."
if docker ps | grep -q panda-pdp10; then
    echo -e "${GREEN}✓ PDP-10 container running${NC}"
else
    echo -e "${RED}✗ PDP-10 container not running${NC}"
    docker logs panda-pdp10 | tail -20
    exit 1
fi

if docker ps | grep -q panda-vax; then
    echo -e "${GREEN}✓ VAX container running${NC}"
else
    echo -e "${RED}✗ VAX container not running${NC}"
    exit 1
fi

echo ""
echo "Step 7: Running Python tests..."
python3 arpanet/scripts/test_panda_vax.py || {
    echo -e "${YELLOW}Warning: Some tests failed${NC}"
}

echo ""
echo "Step 8: Checking PDP-10 logs..."
docker logs panda-pdp10 | tail -10

echo ""
echo "=========================================="
echo -e "${GREEN}Basic test complete!${NC}"
echo ""
echo "Next steps for manual verification:"
echo "1. Connect to VAX: telnet localhost 2323"
echo "2. From VAX, ping PDP-10: ping 172.20.0.40"
echo "3. Test FTP: ftp 172.20.0.40"
echo ""
echo "To stop services:"
echo "  docker-compose -f docker-compose.panda-vax.yml down"
echo "=========================================="
