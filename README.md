# brfid.github.io

Source for [jockeyholler.net](https://www.jockeyholler.net/) — a Hugo-based personal site and technical writing portfolio deployed to GitHub Pages.

The live site is built and deployed via a Hugo + vintage computing pipeline (VAX/PDP-11 via SIMH). The vintage pipeline generates rendered artifacts that Hugo includes in the final build.

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

**Publish:** push a `publish-*` tag → GitHub Actions runs the vintage pipeline and deploys to GitHub Pages.

---

## Vintage pipeline (publish path)

Generates four Hugo input artifacts and drops them into place before the Hugo build:

- `hugo/static/brad.man.txt` — resume rendered by `nroff -man` on PDP-11 (2.11BSD)
- `hugo/static/brad.bio.txt` — plain-text bio block emitted by `bradman.c -mode bio` on VAX
- `hugo/static/build.log.html` — machine-boundary build log with VAX and PDP-11 console sections
- `hugo/data/bio.yaml` — parsed from `brad.bio.txt`; `label`, `principal_headline`,
  `impact_highlights`, and `summary` are vintage-pipeline generated;
  `about` is read from `resume.yaml` top-level field on each build

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

**Publish:** push a `publish-*` tag → CI does a minimal bootstrap:

1. authenticates to AWS via static credentials (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`),
2. starts the edcloud instance (if needed),
3. invokes a single SSM command that runs `scripts/edcloud-vintage-runner.sh` on edcloud,
4. extracts `brad.man.txt` from runner output into `hugo/static/brad.man.txt`,
5. parses `brad.bio.txt` into `hugo/data/bio.yaml` (including principal homepage fields),
6. builds Hugo and deploys Pages,
7. best-effort stops edcloud if the workflow started it.

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
