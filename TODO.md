# TODO

## Decisions (current)

- Build: Python CLI (later TUI).
- Resume source: root `resume.json` (JSON Resume).
- Render: Jinja2 HTML + CSS; PDF via Playwright.
- Output dir: `site/` (deploy root); generated outputs are not committed.
- Deploy: GitHub Pages via Actions; resume generation currently disabled in CI (landing only).
- Indexing: best-effort `noindex/noarchive` + `site/robots.txt`.
- Quality: typed model via `TypedDict`; `mypy` + `pytest` enabled.
- Demo (next): PDP-11 via SIMH; produce a small log artifact and link it from landing.

## Next

- PDP-11 SIMH stage: “tape round-trip” of `resume.json` → log/checksum artifact.
- Optional: add a separate CI workflow to run `pytest`/`mypy` on PRs without deploying.
