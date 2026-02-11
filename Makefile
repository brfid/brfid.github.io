# ARPANET Build Integration - Makefile
# Convenience commands for testing and development

.PHONY: help test test_docker test_aws check_env clean build up down logs chaosnet-build chaosnet-up chaosnet-down chaosnet-logs chaosnet-test aws-up aws-ssh aws-down aws-test aws-status aws-teardown-imps publish publish_arpanet docs

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
	@echo "  make aws-teardown-imps  Tear down archived IMP containers on AWS"
	@echo ""
	@echo "Chaosnet-Direct (active topology):"
	@echo "  make chaosnet-build  Build Chaosnet-direct containers"
	@echo "  make chaosnet-up     Start Chaosnet-direct topology"
	@echo "  make chaosnet-down   Stop Chaosnet-direct topology"
	@echo "  make chaosnet-logs   Show Chaosnet container logs"
	@echo "  make chaosnet-test   Run Chaosnet transfer test"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish       Fast publish (Mode 3)"
	@echo "  make publish_arpanet  Full ARPANET publish (Mode 4)"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          Generate API docs from docstrings into site/api"
	@echo ""
	@echo "Archived (IMP chain — blocked on HI1 framing):"
	@echo "  Compose files in arpanet/archived/"
	@echo "  See arpanet/archived/README.md"
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

aws-teardown-imps:
	@echo "Tearing down archived IMP containers on old t3.medium..."
	@ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 \
		"cd brfid.github.io && docker compose -f arpanet/archived/docker-compose.arpanet.phase2.yml down 2>/dev/null; true"
	@echo "✅ IMP containers stopped"
	@echo ""
	@echo "Consider terminating the t3.medium instance after new t3.micro VMs are up."

# Chaosnet-Direct operations (active topology)
chaosnet-build:
	@echo "Building Chaosnet-direct containers..."
	@docker compose -f docker-compose.arpanet.chaosnet.yml build

chaosnet-up:
	@echo "Starting Chaosnet-direct topology (VAX <-> PDP-10/ITS)..."
	@docker compose -f docker-compose.arpanet.chaosnet.yml up -d
	@echo "Waiting for boot (60s)..."
	@sleep 60
	@echo "✅ Chaosnet topology ready"
	@echo ""
	@echo "Connect to VAX console:    telnet localhost 2323"
	@echo "Connect to PDP-10 console: telnet localhost 2326"

chaosnet-down:
	@echo "Stopping Chaosnet-direct topology..."
	@docker compose -f docker-compose.arpanet.chaosnet.yml down

chaosnet-logs:
	@echo "=== VAX Logs ==="
	@docker logs arpanet-vax --tail 50
	@echo ""
	@echo "=== Chaosnet Shim Logs ==="
	@docker logs arpanet-chaosnet-shim --tail 50
	@echo ""
	@echo "=== PDP-10 Logs ==="
	@docker logs arpanet-pdp10 --tail 50

chaosnet-test:
	@echo "Running Chaosnet transfer test..."
	@.venv/bin/python arpanet/scripts/test_chaosnet_transfer.py

clean:
	@echo "Cleaning up containers and volumes..."
	@docker compose -f docker-compose.arpanet.chaosnet.yml down -v 2>/dev/null; true
	@echo "✅ Cleanup complete"

# Publishing
publish:
	@./scripts/publish-local.sh

publish_arpanet:
	@./scripts/publish-arpanet.sh

docs:
	@.venv/bin/pdoc resume_generator arpanet_logging arpanet -o site/api --docformat google
