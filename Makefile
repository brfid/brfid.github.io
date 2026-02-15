# brfid.github.io Makefile
# Minimal active workflow commands.

.PHONY: help test test_docker check_env clean \
        aws-start aws-stop aws-status \
        publish publish-vintage publish_arpanet docs

help:
	@echo "brfid.github.io - Active Make Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run fast unit test lane"
	@echo "  make test_docker   Deprecated legacy target (no-op)"
	@echo "  make check_env     Verify local prerequisites"
	@echo ""
	@echo "edcloud lifecycle:"
	@echo "  make aws-status    Check edcloud instance status"
	@echo "  make aws-start     Start edcloud instance"
	@echo "  make aws-stop      Stop edcloud instance"
	@echo ""
	@echo "Publishing:"
	@echo "  make publish          Fast local publish"
	@echo "  make publish-vintage  Distributed vintage publish"
	@echo "  make publish_arpanet  Legacy alias for publish-vintage"
	@echo ""
	@echo "Docs:"
	@echo "  make docs          Generate API docs into site/api"

test:
	@echo "Running unit tests..."
	@.venv/bin/python -m pytest -q -m "unit and not docker and not slow"

test_docker:
	@echo "Legacy Docker integration harness removed from this repo."
	@echo "Use publish-vintage workflow lanes for end-to-end vintage validation."

check_env:
	@echo "Checking prerequisites..."
	@command -v docker >/dev/null 2>&1 || { echo "Docker not found"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "Docker Compose plugin not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Python 3 not found"; exit 1; }
	@echo "Environment OK"

aws-status:
	@./aws-status.sh

aws-start:
	@./aws-start.sh

aws-stop:
	@./aws-stop.sh

clean:
	@echo "Stopping production compose stack (if running)..."
	@docker compose -f docker-compose.production.yml down 2>/dev/null || true
	@echo "Cleanup complete"

publish:
	@./scripts/publish-local.sh

publish-vintage:
	@./scripts/publish-vintage.sh

publish_arpanet: publish-vintage

docs:
	@.venv/bin/pdoc resume_generator host_logging -o site/api --docformat google
