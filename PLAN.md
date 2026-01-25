# PLAN

## Goal

Recruiter-friendly landing page that also provides a quiet technical signal via a generated Unix man page.

## Public site (UX)

- Conventional landing page:
  - Clear name/title
  - Links: LinkedIn + resume PDF
- Secondary artifact on the page:
  - A Unix man-page–style summary (`brad(1)`) rendered on-page
  - A short, muted build transcript proving generation (compile → generate → nroff/man output)
- Tone: understated/professional (docs-as-code + CI automation), not retro cosplay.

## Source of truth

- `resume.yaml` (JSON Resume data, stored as YAML).

## Build outputs (generated; not committed)

- Static deploy root: `site/`
- Planned outputs (when resume publishing is re-enabled):
  - `site/resume.pdf`
  - `site/brad.1` (man page source, or preformatted text)
  - `site/brad.txt` (rendered man page shown on the landing page)
  - `site/pdp11-build.log` (muted transcript)

## Generator (local-first)

- Primary interface: Python CLI (later: TUI).
- Rendering:
  - HTML/CSS via Jinja2
  - PDF via Playwright
- Quality gates (run frequently): ruff, mypy, pytest, pylint, vulture.

## CI/CD

- GitHub Actions deploys `site/` to GitHub Pages.
- Resume generation is currently disabled in CI (landing-only) until content issues are resolved.
- When re-enabled, CI should regenerate outputs when inputs change:
  - `resume.yaml`, `templates/**`, `resume_generator/**`, `pyproject.toml`

## SIMH stage (technical artifact)

- v1 target: PDP-11 via SIMH.
- Build behavior:
  1. Convert `resume.yaml` to a compact intermediate (if needed).
  2. In SIMH guest: compile a small C program that emits `brad(1)` from structured data.
  3. Run nroff/man tools in the guest to produce the rendered text.
  4. Copy artifacts back to host (log + rendered manpage) for publishing in `site/`.
- Fallback if PDP-11 constraints become painful: VAX + 4.2/4.3BSD family image for reliability.
- Keep licensing/redistribution in mind for any OS images.

## Inspiration / compatibility

- Compatible with historical networking/system reconstruction work such as the ARPANET simulation project:
  - `https://github.com/obsolescence/arpanet`

