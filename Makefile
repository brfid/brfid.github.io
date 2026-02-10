# ARPANET Build Integration - Makefile
# Convenience commands for testing and development

.PHONY: help test test_docker test_aws check_env clean build up down logs build-phase2 up-phase2 down-phase2 logs-phase2 test-phase2 test-phase2-hi1-framing test-imp-logging aws-up aws-ssh aws-down aws-test aws-status publish publish_arpanet docs

# Default target
help:
	@echo "ARPANET Build Integration - Make Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test_docker   Run Docker integration tests"
	@echo "  make check_env     Verify prerequisites"
	@echo ""
	@echo "AWS Infrastructure:"
	@echo "  make aws-up        Provision AWS test instance"
	@echo "  make aws-ssh       SSH into AWS instance"
	@echo "  make aws-down      Destroy AWS instance"
	@echo "  make aws-test      Run tests on AWS (provision, test, destroy)"
	@echo "  make aws-status    Show AWS instance status"
	@echo ""
	@echo "Docker Operations:"
	@echo "  make build         Build ARPANET containers"
	@echo "  make up            Start ARPANET network"
	@echo "  make down          Stop ARPANET network"
	@echo "  make logs          Show container logs"
	@echo "  make build-phase2  Build Phase 2 containers (VAX+IMP1+IMP2+PDP10-stub)"
	@echo "  make up-phase2     Start Phase 2 Step 2.2 bootstrap topology"
	@echo "  make down-phase2   Stop Phase 2 bootstrap topology"
	@echo "  make logs-phase2   Show Phase 2 IMP logs"
	@echo "  make test-phase2   Run Phase 2 modem/host-link test"
	@echo "  make test-phase2-hi1-framing  Collect HI1 bad-magic evidence (non-orchestrating)"
	@echo "  make test-imp-logging  Run IMP log collection/parsing test"
	@echo "  make clean         Remove containers and volumes"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish       Fast publish (Mode 3)"
	@echo "  make publish_arpanet  Full ARPANET publish (Mode 4)"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          Generate API docs from docstrings into site/api"
	@echo ""

# Testing
test: test_docker
	@echo "✅ All tests completed"

test_docker:
	@echo "Running Docker integration tests..."
	@./test_infra/docker/test_arpanet.py

test_aws:
	@echo "Checking AWS environment..."
	@./test_infra/aws/setup.sh

check_env:
	@echo "Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found"; exit 1; }
	@command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "⚠️  Python 3 not found"; }
	@echo "✅ Environment OK"

# AWS Infrastructure
aws-up:
	@echo "Provisioning AWS test instance..."
	@./test_infra/scripts/provision.py

aws-ssh:
	@./test_infra/scripts/connect.py

aws-down:
	@echo "Destroying AWS test instance..."
	@./test_infra/scripts/destroy.py

aws-test:
	@echo "Running tests on AWS instance..."
	@./test_infra/scripts/test_remote.py

aws-status:
	@./test_infra/scripts/status.py

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

build-phase2:
	@echo "Building ARPANET Phase 2 containers..."
	@docker compose -f docker-compose.arpanet.phase2.yml build

up-phase2:
	@echo "Starting ARPANET Phase 2 Step 2.2 bootstrap topology..."
	@docker compose -f docker-compose.arpanet.phase2.yml up -d
	@echo "Waiting for initial boot (75s)..."
	@sleep 75
	@echo "✅ Phase 2 bootstrap topology ready"
	@echo ""
	@echo "Connect to VAX console:  telnet localhost 2323"
	@echo "Connect to IMP1 console: telnet localhost 2324"
	@echo "Connect to IMP2 console: telnet localhost 2325"
	@echo "PDP10 stub logs:        docker logs arpanet-pdp10 --tail 20"

down-phase2:
	@echo "Stopping ARPANET Phase 2 bootstrap topology..."
	@docker compose -f docker-compose.arpanet.phase2.yml down

logs-phase2:
	@echo "=== IMP1 Logs ==="
	@docker logs arpanet-imp1 --tail 50
	@echo ""
	@echo "=== IMP2 Logs ==="
	@docker logs arpanet-imp2 --tail 50

test-phase2:
	@echo "Running ARPANET Phase 2 modem/host-link test..."
	@.venv/bin/python arpanet/scripts/test_phase2.py

test-phase2-hi1-framing:
	@echo "Collecting ARPANET Phase 2 HI1 framing evidence (non-orchestrating)..."
	@.venv/bin/python arpanet/scripts/test_phase2_hi1_framing.py

test-imp-logging:
	@echo "Running ARPANET IMP log collection/parsing test..."
	@.venv/bin/python arpanet/scripts/test_imp_logging.py

clean:
	@echo "Cleaning up containers and volumes..."
	@docker compose -f docker-compose.arpanet.phase1.yml down -v
	@echo "✅ Cleanup complete"

# Publishing
publish:
	@./scripts/publish-local.sh

publish_arpanet:
	@./scripts/publish-arpanet.sh

docs:
	@.venv/bin/pdoc resume_generator arpanet_logging arpanet -o site/api --docformat google
