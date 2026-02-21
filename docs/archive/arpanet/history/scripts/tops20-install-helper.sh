#!/bin/bash
# TOPS-20 Installation Helper Script
# Run this on AWS instance to prepare for and assist with installation

set -e

AWS_INSTANCE="34.227.223.186"
COMPOSE_FILE="docker-compose.arpanet.phase2.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to check if we're on AWS instance
check_location() {
    if [[ "$HOSTNAME" == *"ip-"* ]]; then
        return 0  # We're on AWS
    else
        return 1  # We're local
    fi
}

# Pre-flight checks
pre_flight_check() {
    print_header "Pre-Flight Check"

    local all_good=true

    # Check 1: Container running
    if docker ps | grep -q arpanet-pdp10; then
        print_success "PDP-10 container is running"
    else
        print_error "PDP-10 container is NOT running"
        all_good=false
    fi

    # Check 2: TOPS-20 tape
    if docker exec arpanet-pdp10 ls /machines/pdp10/tops20_v41.tap &>/dev/null; then
        size=$(docker exec arpanet-pdp10 ls -lh /machines/pdp10/tops20_v41.tap | awk '{print $5}')
        print_success "TOPS-20 tape loaded (${size})"
    else
        print_error "TOPS-20 tape NOT found"
        all_good=false
    fi

    # Check 3: Disk file
    if docker exec arpanet-pdp10 ls /machines/data/tops20.dsk &>/dev/null; then
        size=$(docker exec arpanet-pdp10 ls -lh /machines/data/tops20.dsk | awk '{print $5}')
        print_success "Disk file exists (${size})"
    else
        print_warning "Disk file not found (will be created during installation)"
    fi

    # Check 4: Console port accessible
    if timeout 2 bash -c "echo > /dev/tcp/localhost/2326" 2>/dev/null; then
        print_success "Console port 2326 is accessible"
    else
        print_error "Console port 2326 is NOT accessible"
        all_good=false
    fi

    # Check 5: Other containers running
    local container_count=$(docker ps --filter "name=arpanet-" --format "{{.Names}}" | wc -l)
    print_info "Total ARPANET containers running: ${container_count}/4"

    if [ "$all_good" = true ]; then
        echo
        print_success "All pre-flight checks passed! Ready for installation."
        return 0
    else
        echo
        print_error "Some checks failed. Please fix issues before proceeding."
        return 1
    fi
}

# Show current container status
show_status() {
    print_header "Container Status"
    docker compose -f "$COMPOSE_FILE" ps
}

# Show recent PDP-10 logs
show_logs() {
    print_header "PDP-10 Container Logs (last 30 lines)"
    docker logs arpanet-pdp10 2>&1 | tail -30
}

# Connect to PDP-10 console
connect_console() {
    print_header "Connecting to PDP-10 Console"
    print_info "You are about to connect to the PDP-10 console."
    print_info "To disconnect: Press Ctrl-] then type 'quit'"
    print_warning "Installation will take 1-2 hours. Consider using 'screen' or 'tmux'!"
    echo
    read -p "Press ENTER to connect (or Ctrl-C to cancel)..."
    echo
    telnet localhost 2326
}

# Create installation log file
create_log() {
    local logfile="tops20-install-$(date +%Y%m%d-%H%M%S).log"
    print_header "Creating Installation Log"
    print_info "Starting script session: $logfile"
    print_info "All output will be logged to: $logfile"
    print_info "To stop logging: type 'exit'"
    echo
    read -p "Press ENTER to start logging..."
    script "$logfile"
}

# Check if TOPS-20 is already installed
check_installed() {
    print_header "Checking Installation Status"

    # Try to telnet and check for TOPS-20 prompt
    local response=$(timeout 5 bash -c "echo | telnet localhost 2326" 2>&1 || true)

    if echo "$response" | grep -q "TOPS-20"; then
        print_success "TOPS-20 appears to be running!"
        print_info "You may be able to login directly."
        return 0
    elif echo "$response" | grep -q "sim>"; then
        print_warning "System at sim> prompt - installation needed"
        return 1
    elif echo "$response" | grep -q "MTBOOT"; then
        print_warning "System at MTBOOT> prompt - in installation mode"
        return 1
    else
        print_warning "Could not determine system state"
        return 1
    fi
}

# Backup disk file
backup_disk() {
    print_header "Backing Up Disk File"

    if docker exec arpanet-pdp10 test -f /machines/data/tops20.dsk; then
        local backup_name="tops20.dsk.backup-$(date +%Y%m%d-%H%M%S)"
        docker exec arpanet-pdp10 cp /machines/data/tops20.dsk "/machines/data/$backup_name"
        print_success "Backup created: $backup_name"
    else
        print_warning "No disk file to backup"
    fi
}

# Main menu
show_menu() {
    print_header "TOPS-20 Installation Helper"
    echo "What would you like to do?"
    echo
    echo "  1) Pre-flight check"
    echo "  2) Show container status"
    echo "  3) Show PDP-10 logs"
    echo "  4) Check if TOPS-20 is installed"
    echo "  5) Create installation log (with script)"
    echo "  6) Connect to PDP-10 console"
    echo "  7) Backup disk file"
    echo "  8) Restart PDP-10 container"
    echo "  9) View installation guide"
    echo "  0) Exit"
    echo
}

# Restart container
restart_container() {
    print_header "Restarting PDP-10 Container"
    print_warning "This will restart the PDP-10 (any unsaved work will be lost)"
    read -p "Continue? (y/N): " confirm

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        docker compose -f "$COMPOSE_FILE" restart pdp10
        print_success "Container restarted"
        print_info "Waiting 10 seconds for startup..."
        sleep 10
        docker logs arpanet-pdp10 2>&1 | tail -20
    else
        print_info "Cancelled"
    fi
}

# View guide
view_guide() {
    print_header "Installation Guide"
    if [ -f "arpanet/TOPS20-INSTALLATION-GUIDE.md" ]; then
        less arpanet/TOPS20-INSTALLATION-GUIDE.md
    else
        print_error "Installation guide not found!"
        print_info "Expected: arpanet/TOPS20-INSTALLATION-GUIDE.md"
    fi
}

# Main execution
main() {
    # Check if we're on AWS or local
    if ! check_location; then
        print_warning "You appear to be running this locally (not on AWS instance)"
        print_info "To connect to AWS instance: ssh ubuntu@${AWS_INSTANCE}"
        echo
        read -p "Do you want to SSH to AWS now? (y/N): " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            ssh "ubuntu@${AWS_INSTANCE}"
            exit 0
        fi
    fi

    # If arguments provided, run specific command
    case "${1:-}" in
        check)
            pre_flight_check
            exit $?
            ;;
        status)
            show_status
            exit 0
            ;;
        logs)
            show_logs
            exit 0
            ;;
        connect)
            connect_console
            exit 0
            ;;
        log)
            create_log
            exit 0
            ;;
        *)
            # Interactive menu
            while true; do
                show_menu
                read -p "Enter choice [0-9]: " choice
                case $choice in
                    1) pre_flight_check ;;
                    2) show_status ;;
                    3) show_logs ;;
                    4) check_installed ;;
                    5) create_log ;;
                    6) connect_console ;;
                    7) backup_disk ;;
                    8) restart_container ;;
                    9) view_guide ;;
                    0) print_info "Goodbye!"; exit 0 ;;
                    *) print_error "Invalid choice" ;;
                esac
                echo
                read -p "Press ENTER to continue..."
            done
            ;;
    esac
}

# Run main function
main "$@"
