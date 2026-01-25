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
- Planned outputs:
  - `site/resume.pdf`
  - `site/brad.1` (man page source, or preformatted text)
  - `site/brad.txt` (rendered man page shown on the landing page)
  - `site/vax-build.log` (muted transcript)

## Generator (local-first)

- Primary interface: Python CLI (later: TUI).
- Rendering:
  - HTML/CSS via Jinja2
  - PDF via Playwright
- Task runner: `nox` (planned) to provide a single local/CI entrypoint.
- Quality gates (run frequently): ruff, mypy, pytest, pylint, vulture.

## CI/CD

- GitHub Actions publishes on a `publish` tag (`publish` or `publish-*`).
- Publish pipeline (tag-triggered):
  1. Run quality checks (ruff/mypy/pytest/pylint/vulture).
  2. Generate site (HTML + PDF) into `site/`.
  3. Deploy `site/` to GitHub Pages.
- Non-publish pushes to `main` do not deploy.

## SIMH stage (technical artifact)

- v1 target: VAX via SIMH (BSD 4.3 family; prefer Quasijarus for CI reliability).
- Build behavior:
  1. Convert `resume.yaml` to a compact intermediate (if needed).
  2. In SIMH guest: compile a small C program that emits `brad(1)` from structured data.
  3. Run nroff/man tools in the guest to produce the rendered text.
  4. Copy artifacts back to host (log + rendered manpage) for publishing in `site/`.
- Keep licensing/redistribution in mind for any OS images.

## Inspiration / compatibility

- Compatible with historical networking/system reconstruction work such as the ARPANET simulation project:
  - `https://github.com/obsolescence/arpanet`

## Open questions (next)

- `nox` sessions:
  - Which sessions are mandatory on `publish` (vs “occasional”)?
- SIMH inputs:
  - Which VAX BSD image (exact release + checksums) is acceptable to download/cache in CI?
  - Where do we store/pin it (repo vs release artifacts vs cached download)?
- Artifact contract:
  - Exact filenames and minimal transcript content for `site/vax-build.log`.
  - Whether the landing page renders `brad.txt` inline or links out.
