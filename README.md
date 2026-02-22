# brfid.github.io

Source for [jockeyholler.net](https://www.jockeyholler.net/) — a Hugo-based personal site and technical writing portfolio deployed to GitHub Pages.

The repo has two independent build paths: a Hugo content pipeline for the live site, and an optional vintage computing pipeline (VAX/PDP-11 via SIMH) that generates a rendered artifact for inclusion in the Hugo build.

---

## Hugo

Content lives in `hugo/content/`. The site builds with Hugo extended ≥ 0.156.0 (ARM64 binary available from Hugo releases).

**Local preview:**

```bash
hugo server --source hugo
```

Open `http://localhost:1313/`.

**Build to `site/`:**

```bash
hugo --source hugo --destination site
```

**Publish:** push a `publish-fast-*` tag → GitHub Actions builds Hugo and deploys to GitHub Pages.

---

## Vintage pipeline (optional)

Generates `brad.man.txt` — a resume rendered on VAX hardware via SIMH — which drops into `hugo/static/` before the Hugo build.

**Setup:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

**Quality checks:**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy resume_generator host_logging tests
.venv/bin/python -m ruff check resume_generator
```

**Publish:** push a `publish-vintage-*` tag → full pipeline runs in CI (Python quality gates + VAX/PDP-11 build + Hugo).

Infrastructure lifecycle (starting/stopping the edcloud instance) is managed separately: [brfid/edcloud](https://github.com/brfid/edcloud).

```bash
.venv/bin/python scripts/edcloud_lifecycle.py start
.venv/bin/python scripts/edcloud_lifecycle.py status
.venv/bin/python scripts/edcloud_lifecycle.py stop
```

---

## Source of truth

| Doc | Role |
|-----|------|
| `CHANGELOG.md` (`[Unreleased]`) | Current project state, active priorities, blockers, decisions |
| `CHANGELOG.md` (dated entries) | Chronological change history and milestone evidence |
| `WORKFLOWS.md` | CI/test/publish behavior |
| `ARCHITECTURE.md` | System design |
| `docs/INDEX.md` | Documentation hub |

## Cold start order

1. This file
2. `CHANGELOG.md` (`[Unreleased]` first, then latest dated entries)
3. `hugo/` (Hugo site root — theme, content, config)
4. `docs/INDEX.md`

Then apply `AGENTS.md` constraints.
