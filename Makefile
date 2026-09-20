PYTHON ?= .venv/bin/python
PREVIEW_PORT ?= 1313
BUILD_ROOT ?= build
OUTPUT_DIR ?= site
HUGO_EXTRA ?=

.PHONY: help test test-unit check verify-site check_env clean prepare-site \
        hugo-build resume-pdf resume-pdf-application preview

help:
	@echo "brfid.github.io commands"
	@echo "  make check                   Run lint, format, type, test, and dead-code checks"
	@echo "  make verify-site             Build and verify the complete public HTML and PDF artifact"
	@echo "  make test                    Run unit, browser, and workflow contract tests"
	@echo "  make test-unit               Run tests that do not need Hugo or a local browser"
	@echo "  make check_env               Verify local prerequisites"
	@echo "  make hugo-build              Build HTML only into site/"
	@echo "  make resume-pdf              Build public HTML and phone-free site/resume.pdf"
	@echo "  make resume-pdf-application  Also build the private application PDF outside site/"
	@echo "  make preview                 Serve an isolated local preview and PDF"
	@echo "  make clean                   Remove generated artifacts and tool caches"

test:
	@$(PYTHON) -m pytest -q

test-unit:
	@$(PYTHON) -m pytest -q -m "not integration"

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
	@find . -name .venv -prune -o -name .git -prune -o -type d -name __pycache__ -print0 \
		| xargs -0 rm -rf

prepare-site:
	@mkdir -p $(BUILD_ROOT)/hugo-data
	@cp site.yaml $(BUILD_ROOT)/hugo-data/site.yaml
	@cp resume.yaml $(BUILD_ROOT)/hugo-data/resume.yaml

hugo-build: prepare-site
	@HUGO_DATADIR=../$(BUILD_ROOT)/hugo-data HUGO_RESOURCEDIR=../$(BUILD_ROOT)/hugo-resources \
		hugo --source hugo --destination ../$(OUTPUT_DIR) --cacheDir $(CURDIR)/$(BUILD_ROOT)/hugo-cache \
		--cleanDestinationDir --panicOnWarning $(HUGO_EXTRA)

resume-pdf: check_env hugo-build
	@$(PYTHON) -m site_tools.pdf --site-dir $(OUTPUT_DIR) --output $(OUTPUT_DIR)/resume.pdf

resume-pdf-application: verify-site
	@$(PYTHON) -m site_tools.pdf --site-dir site --output local/bradley-fidler-resume.pdf \
		--private-overlay resume.private.yaml

preview:
	@$(MAKE) resume-pdf BUILD_ROOT=local/preview OUTPUT_DIR=local/preview/site
	@HUGO_DATADIR=../local/preview/hugo-data HUGO_RESOURCEDIR=../local/preview/hugo-resources \
		hugo server --source hugo --destination ../local/preview/site --cacheDir $(CURDIR)/local/preview/hugo-cache \
		--disableFastRender --port $(PREVIEW_PORT)
