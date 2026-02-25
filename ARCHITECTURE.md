# Architecture

Companion docs:
- `README.md`
- `WORKFLOWS.md`
- `docs/integration/INDEX.md`

This repo is a Hugo-based personal site and technical writing portfolio.
The vintage pipeline is optional and produces one Hugo input artifact: `hugo/static/brad.man.txt`.

---

## System boundary

Control plane and execution plane are intentionally split.

- Control plane (GitHub Actions): tag handling, AWS start/stop, SSM invocation, artifact extraction, Hugo deploy.
- Execution plane (edcloud host): all VAX/PDP-11 orchestration in one script, `scripts/edcloud-vintage-runner.sh`.

Hugo remains the site generator in all modes.

---

## Publish modes

### Local publish (`publish-fast-*`)

1. Sync `resume.yaml` to `hugo/data/resume.yaml`
2. Build: `hugo --source hugo --destination site`
3. Deploy `site/` to GitHub Pages

### Vintage publish (`publish-vintage-*`)

1. GitHub Actions assumes AWS role via OIDC
2. Resolve + start edcloud instance
3. Run one SSM command on edcloud
4. edcloud runner executes VAX/PDP-11 stages and emits `brad.man.txt` as base64 markers
5. GitHub Actions writes artifact to `hugo/static/brad.man.txt`
6. Hugo build + GitHub Pages deploy
7. Stop edcloud if workflow started it

---

## Vintage runtime flow (on edcloud)

Entrypoint: `scripts/edcloud-vintage-runner.sh`

1. Prepare host runtime (`.venv`, dependencies, compose stack)
2. Generate `build/vintage/resume.vintage.yaml`
3. Stage 1: VAX compile + manpage generation + uuencode
4. Stage 2: console transfer VAX → PDP-11
5. Stage 3: PDP-11 validation (`uudecode` + `nroff`)
6. Stage 4: host-side render to `build/vintage/brad.txt`
7. Copy `build/vintage/brad.txt` to `hugo/static/brad.man.txt`
8. Emit artifact markers for SSM output parsing
9. Run standard cleanup on exit (screen sessions, `docker compose down --remove-orphans --volumes`, temp files)

---

## Key artifacts

Input:
- `resume.yaml`

Generated (internal):
- `build/vintage/resume.vintage.yaml`
- `build/vintage/brad.1`
- `build/vintage/brad.txt`

Published input to Hugo:
- `hugo/static/brad.man.txt`

Site output:
- `site/`

---

## Operational principles

- Single orchestration implementation for vintage stages (`scripts/edcloud-vintage-runner.sh`).
- CI contains bootstrap logic only; no embedded multi-stage console choreography.
- edcloud lifecycle can be automated end-to-end without manual pre-start.
- Runtime cleanup defaults are deterministic; opt out with `KEEP_RUNTIME=1` for debugging.
- Use additive docs and changelog updates when runtime truth changes.
