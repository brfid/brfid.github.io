#!/bin/bash
# Test script for VAX + IMP Phase 1 connectivity
#
# This script helps validate that the VAX and IMP are properly connected
# and can communicate over the ARPANET network.

set -e

echo "========================================="
echo "ARPANET Phase 1 Connectivity Test"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker Compose is running
echo -e "${YELLOW}Step 1: Checking if containers are running...${NC}"
if docker ps | grep -q "arpanet-vax" && docker ps | grep -q "arpanet-imp1"; then
    echo -e "${GREEN}✓ Both VAX and IMP containers are running${NC}"
else
    echo -e "${RED}✗ Containers not running. Start with:${NC}"
    echo "  docker-compose -f docker-compose.arpanet.phase1.yml up -d"
    exit 1
fi
echo ""

# Check VAX logs
echo -e "${YELLOW}Step 2: Checking VAX boot status...${NC}"
docker logs arpanet-vax 2>&1 | tail -10
echo ""

# Check IMP logs
echo -e "${YELLOW}Step 3: Checking IMP status...${NC}"
docker logs arpanet-imp1 2>&1 | tail -10
echo ""

# Network connectivity
echo -e "${YELLOW}Step 4: Checking network connectivity...${NC}"
echo "VAX IP: $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' arpanet-vax)"
echo "IMP IP: $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' arpanet-imp1)"
echo ""

# Check if ports are listening
echo -e "${YELLOW}Step 5: Checking UDP ports...${NC}"
echo "Checking VAX UDP port 2000..."
docker exec arpanet-vax sh -c "netstat -u 2>/dev/null || ss -u 2>/dev/null || echo 'netstat not available'" | grep -i "2000" || echo "  (Port status not directly visible from outside container)"
echo ""

echo -e "${YELLOW}Step 6: Instructions for manual testing...${NC}"
echo ""
echo "To connect to VAX console:"
echo "  telnet localhost 2323"
echo "  login: root"
echo "  (no password in base image)"
echo ""
echo "Then check network interface:"
echo "  /etc/ifconfig de0"
echo "  netstat -rn"
echo ""
echo "To connect to IMP console (debugging):"
echo "  telnet localhost 2324"
echo ""
echo -e "${GREEN}Test script complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Connect to VAX console and check network interface"
echo "2. Monitor IMP logs for host connection messages"
echo "3. Check for packet exchange in IMP debug output"
