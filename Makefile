# brfid.github.io Makefile
# Minimal active workflow commands.

.PHONY: help test check_env clean \
        sync-resume-data hugo-build resume-pdf \
        aws-start aws-stop aws-status docs

help:
	@echo "brfid.github.io - Active Make Commands"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run fast unit test lane"
	@echo "  make check_env     Verify local prerequisites"
	@echo ""
	@echo "edcloud lifecycle:"
	@echo "  make aws-status    Check edcloud instance status"
	@echo "  make aws-start     Start edcloud instance"
	@echo "  make aws-stop      Stop edcloud instance"
	@echo ""
	@echo "Building:"
	@echo "  make sync-resume-data Sync resume.yaml -> hugo/data/resume.yaml"
	@echo "  make hugo-build       Sync resume data and build Hugo into site/"
	@echo "  make resume-pdf       Generate hugo/static/resume.pdf via resume_generator"
	@echo ""
	@echo "Docs:"
	@echo "  make docs          Generate API docs into site/api"

test:
	@echo "Running unit tests..."
	@.venv/bin/python -m pytest -q -m "unit and not docker and not slow"

check_env:
	@echo "Checking prerequisites..."
	@command -v hugo >/dev/null 2>&1 || { echo "Hugo not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Python 3 not found"; exit 1; }
	@echo "Environment OK"

aws-status:
	@./aws-status.sh

aws-start:
	@./aws-start.sh

aws-stop:
	@./aws-stop.sh

clean:
	@echo "Removing generated build artifacts..."
	@rm -rf build/ site/
	@echo "Cleanup complete"

sync-resume-data:
	@cp resume.yaml hugo/data/resume.yaml
	@echo "Synced resume.yaml -> hugo/data/resume.yaml"

hugo-build: sync-resume-data
	@hugo --source hugo --destination ../site

resume-pdf:
	@.venv/bin/python -c "from pathlib import Path; import shutil; from resume_generator.cli import build_html; from resume_generator.pdf import build_pdf; out=Path('build/resume-pdf'); build_html(src=Path('resume.yaml'), out_dir=out, templates_dir=Path('templates')); pdf=build_pdf(out_dir=out, resume_url_path='/resume/', pdf_name='resume.pdf'); Path('hugo/static').mkdir(parents=True, exist_ok=True); shutil.copy2(pdf, Path('hugo/static/resume.pdf'))"
	@echo "Generated hugo/static/resume.pdf"

docs:
	@.venv/bin/pdoc resume_generator -o site/api --docformat google
