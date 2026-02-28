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
hugo --source hugo --destination ../site
```

Note: `--destination` is relative to the source directory, so `../site` writes to `site/` at the repo root.

**Publish:** push a `publish-fast-*` tag → GitHub Actions builds Hugo and deploys to GitHub Pages.

---

## Vintage pipeline (optional)

Generates `brad.man.txt` — a resume rendered on VAX/PDP-11 via SIMH — and drops it into `hugo/static/` before the Hugo build.

The pipeline uses **pexpect** to drive SIMH emulators via stdin/stdout (no telnet ports, no sleep-based timing):

- **Stage A**: PDP-11 (2.11BSD) runs `nroff -man` to render `brad.1` → `brad.man.txt` (`scripts/pdp11_pexpect.py`)
- **Stage B**: VAX (4.3BSD) compiles and runs `bradman.c` to generate `brad.1` from `resume.vintage.yaml` (`scripts/vax_pexpect.py`)
- **Stage A+B**: VAX generates, host couriers the file, PDP-11 renders

Both stages are implemented and validated on `main`. See `CHANGELOG.md` for validation details.

See `ARCHITECTURE.md` and `docs/integration/INDEX.md` for design details.

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

**Publish:** push a `publish-vintage-*` tag → CI does a minimal bootstrap:

1. authenticates to AWS via static credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`),
2. starts the edcloud instance (if needed),
3. invokes a single SSM command that runs `scripts/edcloud-vintage-runner.sh` on edcloud,
4. extracts `brad.man.txt` from runner output into `hugo/static/brad.man.txt`,
5. builds Hugo and deploys Pages,
6. best-effort stops edcloud if the workflow started it.

Single orchestration entrypoint: `scripts/edcloud-vintage-runner.sh`.
Set `KEEP_IMAGES=1` to preserve Docker images between runs (avoids rebuild on retry).

Infrastructure lifecycle managed separately: [brfid/edcloud](https://github.com/brfid/edcloud).

**Vintage CI prerequisites:**

- edcloud EC2 instance must be SSM-managed (SSM Agent + IAM permissions).
- GitHub repo secrets:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_REGION`
  - optional `EDCLOUD_INSTANCE_ID` (otherwise instance resolves by `edcloud` tags).

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
