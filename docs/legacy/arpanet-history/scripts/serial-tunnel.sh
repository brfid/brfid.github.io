#!/bin/bash
# Serial-over-TCP Tunnel Setup for VAX + PDP-10
# Phase 1: Establish tunnel between VAX and PDP-10 consoles
#
# Usage:
#   ./arpanet/scripts/serial-tunnel.sh start    # Start tunnel
#   ./arpanet/scripts/serial-tunnel.sh stop     # Stop tunnel
#   ./arpanet/scripts/serial-tunnel.sh status   # Check tunnel status

set -e

VAX_CONSOLE_PORT=2323
PDP10_CONSOLE_PORT=2326
VAX_TUNNEL_PORT=9000
PDP10_TUNNEL_PORT=9001

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_socat() {
    if ! command -v socat &> /dev/null; then
        log_error "socat not found. Installing..."
        apt-get update && apt-get install -y socat
    fi
}

start_tunnel() {
    log_info "Starting serial tunnel..."
    check_socat

    # Check if containers are running
    if ! docker ps --format '{{.Names}}' | grep -q "arpanet-vax"; then
        log_error "VAX container not running. Start it first:"
        echo "  docker-compose -f docker-compose.vax-pdp10-serial.yml up -d vax"
        exit 1
    fi

    if ! docker ps --format '{{.Names}}' | grep -q "arpanet-pdp10"; then
        log_error "PDP-10 container not running. Start it first:"
        echo "  docker-compose -f docker-compose.vax-pdp10-serial.yml up -d pdp10"
        exit 1
    fi

    # Kill any existing socat processes in containers
    log_info "Cleaning up existing tunnel processes..."
    docker exec arpanet-vax pkill -9 socat 2>/dev/null || true
    docker exec arpanet-pdp10 pkill -9 socat 2>/dev/null || true

    # Start VAX redirect
    log_info "Starting VAX redirect on port ${VAX_TUNNEL_PORT}..."
    docker exec -d arpanet-vax socat TCP-LISTEN:${VAX_TUNNEL_PORT},bind=127.0.0.1,fork TCP:localhost:${VAX_CONSOLE_PORT}

    # Start PDP-10 redirect
    log_info "Starting PDP-10 redirect on port ${PDP10_TUNNEL_PORT}..."
    docker exec -d arpanet-pdp10 socat TCP-LISTEN:${PDP10_TUNNEL_PORT},bind=127.0.0.1,fork TCP:localhost:${PDP10_CONSOLE_PORT}

    # Give redirects time to bind
    sleep 2

    # Start cross-connect tunnel
    log_info "Starting cross-connect tunnel..."
    docker exec -d arpanet-vax socat TCP:127.0.0.1:${VAX_TUNNEL_PORT} TCP:127.0.0.1:${PDP10_TUNNEL_PORT}

    log_info "Tunnel started successfully!"
    echo ""
    echo "Connect to VAX console:  telnet localhost ${VAX_TUNNEL_PORT}"
    echo "Connect to PDP-10 console: telnet localhost ${PDP10_TUNNEL_PORT}"
    echo ""
    echo "To verify tunnel:"
    echo "  telnet localhost ${VAX_TUNNEL_PORT}   # Type something, it should appear on PDP-10"
}

stop_tunnel() {
    log_info "Stopping tunnel..."
    docker exec arpanet-vax pkill -9 socat 2>/dev/null || true
    docker exec arpanet-pdp10 pkill -9 socat 2>/dev/null || true
    log_info "Tunnel stopped."
}

status_tunnel() {
    echo "Serial Tunnel Status"
    echo "===================="
    echo ""
    echo "Ports:"
    echo "  VAX tunnel:   localhost:${VAX_TUNNEL_PORT} -> container:${VAX_CONSOLE_PORT}"
    echo "  PDP-10 tunnel: localhost:${PDP10_TUNNEL_PORT} -> container:${PDP10_CONSOLE_PORT}"
    echo ""

    echo "Running processes:"
    docker exec arpanet-vax ps aux | grep socat || echo "  (none)"
    docker exec arpanet-pdp10 ps aux | grep socat || echo "  (none)"
    echo ""

    echo "Port listeners:"
    netstat -tlnp 2>/dev/null | grep -E "(${VAX_TUNNEL_PORT}|${PDP10_TUNNEL_PORT})" || \
        ss -tlnp 2>/dev/null | grep -E "(${VAX_TUNNEL_PORT}|${PDP10_TUNNEL_PORT})" || \
        echo "  (no listeners found - start tunnel first)"
}

case "$1" in
    start)
        start_tunnel
        ;;
    stop)
        stop_tunnel
        ;;
    status)
        status_tunnel
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
