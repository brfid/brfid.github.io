PYTHON ?= .venv/bin/python
PREVIEW_PORT ?= 1313

.PHONY: help test check verify-site check_env clean prepare-site new-post \
        hugo-build resume-pdf resume-pdf-application preview preview-drafts

help:
	@echo "brfid.github.io commands"
	@echo "  make check                   Run lint, format, type, test, and dead-code checks"
	@echo "  make verify-site             Build and verify the complete public HTML and PDF artifact"
	@echo "  make test                    Run unit and workflow contract tests"
	@echo "  make check_env               Verify local prerequisites"
	@echo "  make hugo-build              Build HTML only into site/"
	@echo "  make resume-pdf              Build public HTML and phone-free site/resume.pdf"
	@echo "  make resume-pdf-application  Also build the private application PDF outside site/"
	@echo "  make preview                 Serve the public site and PDF locally"
	@echo "  make preview-drafts          Include draft posts in the local preview"
	@echo "  make new-post POST_SLUG=name  Scaffold a draft post bundle"
	@echo "  make clean                   Remove generated artifacts and tool caches"

test:
	@$(PYTHON) -m pytest -q

check:
	@$(PYTHON) -m ruff check site_tools tests
	@$(PYTHON) -m ruff format --check site_tools tests
	@$(PYTHON) -m mypy site_tools tests
	@$(PYTHON) -m pytest -q
	@$(PYTHON) -m pylint site_tools -sn
	@$(PYTHON) -m vulture --config pyproject.toml site_tools

verify-site: resume-pdf
	@$(PYTHON) -m site_tools.verify site

check_env:
	@$(PYTHON) -m site_tools.environment
	@echo "Environment OK: Hugo, Python, Playwright, Chromium, and PDF inspection tools are available"

clean:
	@rm -rf build/ site/ local/ .mypy_cache/ .pytest_cache/ .ruff_cache/
	@rm -f hugo/.hugo_build.lock hugo/data/resume.yaml hugo/data/site.yaml
	@rm -f hugo/data/bio.yaml hugo/static/build.log.html hugo/static/pipeline-status.json hugo/static/brad.bio.txt
	@find . -name .venv -prune -o -name .git -prune -o -type d -name __pycache__ -print0 \
		| xargs -0 rm -rf

prepare-site:
	@mkdir -p hugo/data
	@cp site.yaml hugo/data/site.yaml
	@cp resume.yaml hugo/data/resume.yaml
	@# Clear retired generated inputs in existing checkouts before Hugo copies static files.
	@rm -f hugo/data/bio.yaml hugo/static/build.log.html hugo/static/pipeline-status.json hugo/static/brad.bio.txt

new-post:
	@test -n "$(POST_SLUG)" || { echo "Usage: make new-post POST_SLUG=my-post"; exit 2; }
	@hugo new content --source hugo --kind posts "posts/$(POST_SLUG)"

hugo-build: prepare-site
	@hugo --source hugo --destination ../site --cleanDestinationDir --panicOnWarning

resume-pdf: hugo-build
	@$(PYTHON) -c "from pathlib import Path; from site_tools.pdf import build_pdf; build_pdf(site_dir=Path('site'), resume_url_path='/resume/', pdf_path=Path('site/resume.pdf'))"

resume-pdf-application: verify-site
	@$(PYTHON) -c "from pathlib import Path; from site_tools.pdf import build_pdf; build_pdf(site_dir=Path('site'), resume_url_path='/resume/', pdf_path=Path('local/bradley-fidler-resume.pdf'), private_resume_path=Path('resume.private.yaml'))"

preview: resume-pdf
	@hugo server --source hugo --destination ../site --disableFastRender --port $(PREVIEW_PORT)

preview-drafts: resume-pdf
	@hugo server --source hugo --destination ../site --buildDrafts --disableFastRender --port $(PREVIEW_PORT)
