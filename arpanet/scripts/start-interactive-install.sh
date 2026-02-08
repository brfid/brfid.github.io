#!/bin/bash
# Start Interactive TOPS-20 Installation
# This script starts the one-off interactive installation container

set -e

echo "========================================="
echo "TOPS-20 V4.1 Interactive Installation"
echo "========================================="
echo ""
echo "This will start an interactive SIMH session where you can"
echo "complete the TOPS-20 installation through a direct console."
echo ""
echo "Estimated time: 1-2 hours (mostly waiting for file restoration)"
echo ""
echo "What will happen:"
echo "  1. You'll see the sim> prompt"
echo "  2. Type: boot tua0"
echo "  3. Follow TOPS20-SOLUTION.md steps 4-10"
echo ""
echo "Important:"
echo "  - Use screen/tmux for stability (recommended)"
echo "  - This session must complete without interruption"
echo "  - File restoration takes 30-60 minutes (be patient!)"
echo ""

read -p "Ready to start? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Starting interactive pdp10-ks..."
echo "You should see: sim> prompt"
echo "Then type: boot tua0"
echo ""
echo "========================================="
echo ""

docker run --rm -it \
  --name pdp10-install \
  -v brfid.github.io_arpanet-pdp10-data:/machines/data \
  -v brfid.github.io_arpanet-pdp10-config:/machines/pdp10 \
  brfidgithubio-pdp10 \
  /usr/local/bin/pdp10-ks /machines/pdp10/install.ini

echo ""
echo "========================================="
echo "Installation session ended"
echo ""
echo "Next steps:"
echo "  1. Verify installation completed successfully"
echo "  2. Run: bash reconfigure-production.sh"
echo "  3. Test: docker compose -f docker-compose.arpanet.phase2.yml up -d pdp10"
echo "========================================="
