# ARPANET Build Integration - Makefile
# Convenience commands for testing and development

.PHONY: help test test_docker test_local check_env clean build up down logs

# Default target
help:
	@echo "ARPANET Build Integration - Make Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test_docker   Run Docker integration tests"
	@echo "  make test_local    Check local environment setup"
	@echo "  make check_env     Verify prerequisites"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make build         Build ARPANET containers"
	@echo "  make up            Start ARPANET network"
	@echo "  make down          Stop ARPANET network"
	@echo "  make logs          Show container logs"
	@echo "  make clean         Remove containers and volumes"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish       Fast publish (Mode 3)"
	@echo "  make publish_arpanet  Full ARPANET publish (Mode 4)"
	@echo ""

# Testing
test: test_docker
	@echo "✅ All tests completed"

test_docker:
	@echo "Running Docker integration tests..."
	@./test_infra/docker/test_arpanet.py

test_local:
	@echo "Checking local environment..."
	@./test_infra/local/setup.sh

check_env:
	@echo "Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }
	@command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "⚠️  Python 3 not found"; }
	@echo "✅ Environment OK"

# Docker operations
build:
	@echo "Building ARPANET containers..."
	@docker compose -f docker-compose.arpanet.phase1.yml build

up:
	@echo "Starting ARPANET network..."
	@docker compose -f docker-compose.arpanet.phase1.yml up -d
	@echo "Waiting for VAX boot (60s)..."
	@sleep 60
	@echo "Waiting for IMP boot (10s)..."
	@sleep 10
	@echo "✅ Network ready"
	@echo ""
	@echo "Connect to VAX console: telnet localhost 2323"
	@echo "Connect to IMP console: telnet localhost 2324"

down:
	@echo "Stopping ARPANET network..."
	@docker compose -f docker-compose.arpanet.phase1.yml down

logs:
	@echo "=== VAX Logs ==="
	@docker logs arpanet-vax --tail 50
	@echo ""
	@echo "=== IMP Logs ==="
	@docker logs arpanet-imp1 --tail 50

clean:
	@echo "Cleaning up containers and volumes..."
	@docker compose -f docker-compose.arpanet.phase1.yml down -v
	@echo "✅ Cleanup complete"

# Publishing
publish:
	@./scripts/publish-local.sh

publish_arpanet:
	@./scripts/publish-arpanet.sh
