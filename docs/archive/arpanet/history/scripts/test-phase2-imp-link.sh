#!/bin/bash
# ARPANET Phase 2 test script
# Validates VAX + IMP1 + IMP2 + PDP10-stub bring-up and modem/host-link evidence.

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "ARPANET Phase 2 Link Test"
echo "(VAX + IMP1 + IMP2 + PDP10-stub)"
echo "========================================="
echo ""

echo -e "${YELLOW}Step 1: Checking if phase 2 containers are running...${NC}"
if docker ps | grep -q "arpanet-vax" && \
   docker ps | grep -q "arpanet-imp1" && \
   docker ps | grep -q "arpanet-imp2" && \
   docker ps | grep -q "arpanet-pdp10"; then
    echo -e "${GREEN}✓ VAX, IMP1, IMP2, and PDP10-stub containers are running${NC}"
else
    echo -e "${RED}✗ Required containers not running. Start with:${NC}"
    echo "  docker compose -f docker-compose.arpanet.phase2.yml up -d"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 2: Checking assigned container IPs...${NC}"
echo "VAX : $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' arpanet-vax)"
echo "IMP1: $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' arpanet-imp1)"
echo "IMP2: $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' arpanet-imp2)"
echo "PDP10: $(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' arpanet-pdp10)"
echo ""

echo -e "${YELLOW}Step 3: Checking IMP1 modem-link configuration evidence...${NC}"
if docker logs arpanet-imp1 2>&1 | grep -E "MI1|3001|IMP #1 \(Phase 2\)" >/dev/null; then
    echo -e "${GREEN}✓ IMP1 logs show MI1/Phase 2 startup markers${NC}"
else
    echo -e "${RED}✗ IMP1 logs do not show expected MI1 markers${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 4: Checking IMP2 modem-link configuration evidence...${NC}"
if docker logs arpanet-imp2 2>&1 | grep -E "MI1|3001|IMP #2 \(Phase 2\)" >/dev/null; then
    echo -e "${GREEN}✓ IMP2 logs show MI1/Phase 2 startup markers${NC}"
else
    echo -e "${RED}✗ IMP2 logs do not show expected MI1 markers${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 5: Checking IMP2 host-link (HI1) configuration evidence...${NC}"
if docker logs arpanet-imp2 2>&1 | grep -E "HI1|172\.20\.0\.40|PDP-10 host" >/dev/null; then
    echo -e "${GREEN}✓ IMP2 logs show HI1 host-link startup markers${NC}"
else
    echo -e "${RED}✗ IMP2 logs do not show expected HI1 host-link markers${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 6: Recent IMP log tails for manual inspection...${NC}"
echo "--- IMP1 tail ---"
docker logs arpanet-imp1 2>&1 | tail -20
echo ""
echo "--- IMP2 tail ---"
docker logs arpanet-imp2 2>&1 | tail -20
echo ""

echo -e "${GREEN}Phase 2 link test completed.${NC}"
echo ""
echo "Next manual checks:"
echo "  telnet localhost 2324   # IMP1 console"
echo "  telnet localhost 2325   # IMP2 console"
echo "  docker logs arpanet-pdp10 | tail -20  # PDP10 host stub activity"
echo "Look for MI1 modem traffic and HI1 host-link markers in IMP logs."
