# brfid.github.io Makefile
# Minimal active workflow commands.

PYTHON ?= .venv/bin/python
PREVIEW_PORT ?= 1313

.PHONY: help test check check_env clean \
        sync-site-data sync-resume-data hugo-build \
        resume-pdf resume-pdf-public resume-pdf-application \
        preview preview-public docs

help:
	@echo "brfid.github.io - Active Make Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run fast non-Docker tests"
	@echo "  make check         Run the complete local/CI quality gate"
	@echo "  make check_env     Verify local prerequisites"
	@echo ""
	@echo "Building:"
	@echo "  make sync-site-data    Sync site.yaml -> hugo/data/site.yaml"
	@echo "  make sync-resume-data  Sync resume.yaml -> hugo/data/resume.yaml"
	@echo "  make hugo-build        Build the public site, including resume HTML, into site/"
	@echo "  make resume-pdf             Build the site and public phone-free PDF"
	@echo "  make resume-pdf-public      CI-compatible alias for resume-pdf"
	@echo "  make resume-pdf-application Build a private application PDF outside the web root"
	@echo "  make preview                Serve the production-equivalent site and phone-free PDF"
	@echo "  make preview-public         Compatibility alias for preview"
	@echo ""
	@echo "Docs:"
	@echo "  make docs          Generate API docs into site/api"

test:
	@echo "Running tests..."
	@$(PYTHON) -m pytest -q -m "not docker and not slow"

check:
	@$(PYTHON) -m ruff check resume_generator scripts tests
	@$(PYTHON) -m ruff format --check resume_generator scripts tests
	@$(PYTHON) -m mypy resume_generator tests
	@$(PYTHON) -m pytest -q -m "not docker and not slow"
	@$(PYTHON) -m pylint resume_generator -sn
	@$(PYTHON) -m vulture --config pyproject.toml resume_generator

check_env:
	@echo "Checking prerequisites..."
	@command -v hugo >/dev/null 2>&1 || { echo "Hugo not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Python 3 not found"; exit 1; }
	@echo "Environment OK"

clean:
	@echo "Removing generated build artifacts..."
	@rm -rf build/ site/ local/
	@echo "Cleanup complete"

sync-site-data:
	@mkdir -p hugo/data
	@cp site.yaml hugo/data/site.yaml
	@echo "Synced site.yaml -> hugo/data/site.yaml"

sync-resume-data:
	@mkdir -p hugo/data
	@cp resume.yaml hugo/data/resume.yaml
	@echo "Synced resume.yaml -> hugo/data/resume.yaml"

hugo-build: sync-site-data sync-resume-data
	@hugo --source hugo --destination ../site --cleanDestinationDir

resume-pdf: hugo-build
	@$(PYTHON) -c "from pathlib import Path; from resume_generator.pdf import build_pdf; build_pdf(site_dir=Path('site'), resume_url_path='/resume/', pdf_path=Path('site/resume.pdf'))"
	@echo "Generated public site/resume.pdf"

resume-pdf-public: resume-pdf

resume-pdf-application: hugo-build
	@$(PYTHON) -c "from pathlib import Path; from resume_generator.pdf import build_pdf; build_pdf(site_dir=Path('site'), resume_url_path='/resume/', pdf_path=Path('local/bradley-fidler-resume.pdf'), private_resume_path=Path('resume.private.yaml'))"
	@echo "Generated private local/bradley-fidler-resume.pdf"

preview: resume-pdf
	@hugo server --source hugo --destination ../site --disableFastRender --port $(PREVIEW_PORT)

preview-public: resume-pdf-public
	@hugo server --source hugo --destination ../site --disableFastRender --port $(PREVIEW_PORT)

docs:
	@$(PYTHON) -m pdoc resume_generator -o site/api --docformat google
