#!/bin/bash
# Reconfigure Production PDP-10 to Boot from Installed Disk

set -e

echo "========================================="
echo "Reconfigure Production PDP-10"
echo "========================================="
echo ""
echo "This updates pdp10.ini to boot from the installed disk"
echo "instead of the installation tape."
echo ""

read -p "Continue? (y/N): " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo "Creating production pdp10.ini..."

docker run --rm -i \
  -v brfid.github.io_arpanet-pdp10-config:/machines/pdp10 \
  ubuntu:22.04 bash << 'DOCKEREOF'
cat >/machines/pdp10/pdp10.ini << 'EOF'
; SIMH PDP-10 KS Configuration - TOPS-20 V4.1 Production
; Boots from INSTALLED disk (not installation tape)

set debug stdout
set console wru=034

; Disable unused devices
set dz disabled
set lp20 disabled

; Tape drive (available but not used for boot)
set tua enable
set tua0 locked
attach tua0 /machines/pdp10/tops20_v41.tap

; System disk (INSTALLED)
set rpa enable
set rpa0 rp06
attach rpa0 /machines/data/tops20.dsk

; IMP Network Interface for ARPANET
set imp enabled
set imp debug
attach -u imp 2000:172.20.0.30:2000

; Telnet console for remote access
set console telnet=2323

echo ========================================
echo PDP-10 TOPS-20 V4.1 Production
echo ========================================
echo Console: telnet on port 2323 (host 2326)
echo Disk: Booting from INSTALLED system
echo IMP: Connected to IMP #2 at 172.20.0.30
echo ========================================

; Boot from INSTALLED disk (not tape)
boot rpa0
EOF
DOCKEREOF

echo ""
echo "✅ Production configuration created"
echo ""
echo "Next steps:"
echo "  1. Start container:"
echo "     cd ~/brfid.github.io"
echo "     docker compose -f docker-compose.arpanet.phase2.yml up -d pdp10"
echo ""
echo "  2. Wait 30 seconds, then test:"
echo "     telnet localhost 2326"
echo ""
echo "  3. You should see TOPS-20 login prompt!"
echo ""
echo "========================================="
