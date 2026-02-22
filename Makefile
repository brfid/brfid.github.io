# brfid.github.io Makefile
# Minimal active workflow commands.

.PHONY: help test test_docker check_env clean \
        sync-resume-data hugo-build resume-pdf \
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
	@echo "  make sync-resume-data Sync resume.yaml -> hugo/data/resume.yaml"
	@echo "  make hugo-build       Sync resume data and build Hugo into site/"
	@echo "  make resume-pdf       Generate hugo/static/resume.pdf via resume_generator"
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
	@.venv/bin/python scripts/edcloud_lifecycle.py status

aws-start:
	@.venv/bin/python scripts/edcloud_lifecycle.py start

aws-stop:
	@.venv/bin/python scripts/edcloud_lifecycle.py stop

clean:
	@echo "Stopping production compose stack (if running)..."
	@docker compose -f docker-compose.production.yml down 2>/dev/null || true
	@echo "Cleanup complete"

sync-resume-data:
	@cp resume.yaml hugo/data/resume.yaml
	@echo "Synced resume.yaml -> hugo/data/resume.yaml"

hugo-build: sync-resume-data
	@hugo --source hugo --destination site

resume-pdf:
	@.venv/bin/python -c "from pathlib import Path; import shutil; from resume_generator.cli import build_html; from resume_generator.pdf import build_pdf; out=Path('build/resume-pdf'); build_html(src=Path('resume.yaml'), out_dir=out, templates_dir=Path('templates')); pdf=build_pdf(out_dir=out, resume_url_path='/resume/', pdf_name='resume.pdf'); Path('hugo/static').mkdir(parents=True, exist_ok=True); shutil.copy2(pdf, Path('hugo/static/resume.pdf'))"
	@echo "Generated hugo/static/resume.pdf"

publish:
	@./scripts/publish-local.sh

publish-vintage:
	@./scripts/publish-vintage.sh

publish_arpanet: publish-vintage

docs:
	@.venv/bin/pdoc resume_generator host_logging -o site/api --docformat google
