PYTHON ?= .venv/bin/python
PREVIEW_PORT ?= 1313

.PHONY: help test check verify-site check_env clean \
        sync-site-data sync-resume-data new-post hugo-build \
        resume-pdf resume-pdf-public resume-pdf-application \
        preview preview-drafts preview-public

help:
	@echo "brfid.github.io commands"
	@echo ""
	@echo "Checks:"
	@echo "  make test          Run tests"
	@echo "  make check         Run lint, format, type, test, and dead-code checks"
	@echo "  make verify-site   Clean-build Hugo and verify rendered public contracts"
	@echo "  make check_env     Verify local prerequisites"
	@echo ""
	@echo "Build and preview:"
	@echo "  make sync-site-data    Sync site.yaml -> hugo/data/site.yaml"
	@echo "  make sync-resume-data  Sync resume.yaml -> hugo/data/resume.yaml"
	@echo "  make new-post POST_SLUG=my-post  Scaffold a draft post bundle"
	@echo "  make hugo-build        Build the public site, including resume HTML, into site/"
	@echo "  make resume-pdf             Build the site and public phone-free PDF"
	@echo "  make resume-pdf-public      CI-compatible alias for resume-pdf"
	@echo "  make resume-pdf-application Build a private application PDF outside the web root"
	@echo "  make preview                Serve the production-equivalent site and phone-free PDF"
	@echo "  make preview-drafts         Serve the site with draft blog posts"
	@echo "  make preview-public         Compatibility alias for preview"

test:
	@echo "Running tests..."
	@$(PYTHON) -m pytest -q

check:
	@$(PYTHON) -m ruff check resume_generator scripts tests
	@$(PYTHON) -m ruff format --check resume_generator scripts tests
	@$(PYTHON) -m mypy resume_generator scripts tests
	@$(PYTHON) -m pytest -q
	@$(PYTHON) -m pylint resume_generator scripts -sn
	@$(PYTHON) -m vulture --config pyproject.toml resume_generator scripts

verify-site: sync-site-data sync-resume-data
	@hugo --source hugo --destination "$(abspath build/site-check)" --cleanDestinationDir --panicOnWarning
	@$(PYTHON) scripts/verify_site.py build/site-check

check_env:
	@echo "Checking prerequisites..."
	@command -v "$(PYTHON)" >/dev/null 2>&1 || { echo "Python interpreter not found: $(PYTHON)"; exit 1; }
	@$(PYTHON) scripts/check_environment.py
	@echo "Environment OK: Hugo, Python, Playwright, and pinned Chromium are available"

clean:
	@echo "Removing generated build artifacts..."
	@rm -rf build/ site/ local/
	@rm -f hugo/data/bio.yaml hugo/data/resume.yaml hugo/data/site.yaml
	@rm -f hugo/static/build.log.html hugo/static/pipeline-status.json
	@echo "Cleanup complete"

sync-site-data:
	@mkdir -p hugo/data
	@cp site.yaml hugo/data/site.yaml
	@echo "Synced site.yaml -> hugo/data/site.yaml"

sync-resume-data:
	@mkdir -p hugo/data
	@cp resume.yaml hugo/data/resume.yaml
	@echo "Synced resume.yaml -> hugo/data/resume.yaml"

new-post:
	@test -n "$(POST_SLUG)" || { echo "Usage: make new-post POST_SLUG=my-post"; exit 2; }
	@hugo new content --source hugo --kind posts "posts/$(POST_SLUG)"

hugo-build: sync-site-data sync-resume-data
	@hugo --source hugo --destination ../site --cleanDestinationDir --panicOnWarning

resume-pdf: hugo-build
	@$(PYTHON) -c "from pathlib import Path; from resume_generator.pdf import build_pdf; build_pdf(site_dir=Path('site'), resume_url_path='/resume/', pdf_path=Path('site/resume.pdf'))"
	@echo "Generated public site/resume.pdf"

resume-pdf-public: resume-pdf

resume-pdf-application: hugo-build
	@$(PYTHON) -c "from pathlib import Path; from resume_generator.pdf import build_pdf; build_pdf(site_dir=Path('site'), resume_url_path='/resume/', pdf_path=Path('local/bradley-fidler-resume.pdf'), private_resume_path=Path('resume.private.yaml'))"
	@echo "Generated private local/bradley-fidler-resume.pdf"

preview: resume-pdf
	@hugo server --source hugo --destination ../site --disableFastRender --port $(PREVIEW_PORT)

preview-drafts: resume-pdf
	@hugo server --source hugo --destination ../site --buildDrafts --disableFastRender --port $(PREVIEW_PORT)

preview-public: resume-pdf-public
	@hugo server --source hugo --destination ../site --disableFastRender --port $(PREVIEW_PORT)
