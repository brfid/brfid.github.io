# Plan (brfid.github.io)

## Background / Constraints

- Goal is credible, low-maintenance “portfolio optics”: link to real shipped docs work (company docs site) + keep personal surface area minimal.
- GitHub Pages is static hosting (no server-side app), so the “generator” must run in CI and publish static artifacts.
- Primary scripting language: Python (no JS/TS requirement for this project).

## Goals

- Classy minimal landing page with links (LinkedIn + Resume).
- Resume generated from a single source of truth (JSON Resume) using **Python**.
- Outputs published on GitHub Pages as static files (no server required).

## Non-goals

- Maintaining a full personal site/blog.
- Building a React/TypeScript app just for “versatility”.

## Target UX

- `/` shows a simple landing page with:
  - LinkedIn link
  - Resume (HTML) link (`/resume/`)
  - Resume (PDF) link (`/resume.pdf`)
- `/resume/` is a readable web resume.
- `/resume.pdf` is a downloadable PDF.

## Architecture (static deploy)

- Inputs live in repo:
  - `resume/resume.json` (JSON Resume)
  - `templates/` (Jinja2 HTML + CSS)
  - `resume_site/` (Python CLI + pipeline)
- Outputs are generated (not committed) and written into `public/`:
  - `public/resume/index.html`
  - `public/resume/resume.css`
  - `public/resume.pdf`
- GitHub Pages deploys whatever path the workflow uploads; this repo uploads `public/`.

## Key design decisions

- **Minimal landing page**: keep the public “site” to a simple, stable set of links; expand over time without changing the aesthetic.
- **Generated artifacts are not committed**: avoids binary diffs/merge conflicts and ensures the deployed resume is reproducible from source + pinned deps.
- **PDF via Playwright**: renders the same HTML/CSS as browsers; reliable output and consistent typography/layout.
- **Pluggable pipeline** (future): stage boundaries are file-based CLI steps so additional “demo” stages (e.g. SIMH/virtualized legacy build steps) can plug in later.

## CI/CD

- GitHub Actions runs on `main` pushes with a **paths filter** (resume inputs + generator + landing + workflow).
- Caches:
  - pip dependencies (via `actions/setup-python` pip cache)
  - Playwright browsers (`~/.cache/ms-playwright`)
- Generates artifacts into `public/` then deploys `public/` to Pages.

## Implementation steps

1. Keep resume source format: JSON Resume (`resume/resume.json`).
2. Python generator + templates:
   - `resume-site` CLI (Jinja2) → writes `public/resume/index.html`
3. PDF generation:
   - Playwright renders `/resume/` → writes `public/resume.pdf`
4. GitHub Actions:
   - install python deps
   - cache Playwright browsers
   - generate HTML + PDF
   - deploy `public/`

## Local usage

```bash
python -m pip install -e .
python -m playwright install chromium
resume-site --out public
```

## Notes

- Previous Docusaurus resume site is preserved at `backup/docusaurus-site/`.
