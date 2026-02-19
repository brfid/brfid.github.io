# Agent notes (repo workflow)

## Mission (cold start)

- Build and publish a static resume site, with optional VAX/ARPANET stages used as a technical signal.
- Keep build outputs reproducible and historically grounded where intended (VAX/SIMH + ARPANET tracks).
- Prefer clear, evidence-backed updates over broad speculative changes.
- Keep infrastructure orchestration minimal in this repo; lifecycle control belongs to `edcloud` and should be operable from small ARM controller hosts (for example, Pi Zero 2 class devices).

## Start-here order (for new LLM sessions)

1. `README.md`
2. `docs/COLD-START.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/integration/INDEX.md` (if touching integration/ARPANET history)

## Source-of-truth map

- Current project snapshot: `STATUS.md`
- Documentation hub: `docs/INDEX.md`
- Integration active path + known-good evidence: `docs/integration/INDEX.md`
- Integration history log (retained, not active): `docs/integration/progress/NEXT-STEPS.md`
- Integration progress timeline (retained): `docs/integration/progress/PHASE3-PROGRESS.md`
- Historical transport decisions: `docs/deprecated/transport-archive.md`

## Virtualenv-only

- Use the repo-local venv at `.venv/` for all Python commands.
- Do not install anything globally or modify system Python.

## Commit cadence

Commit at significant milestones so the history stays readable and bisectable. Examples:

- Landing page / UX milestone complete
- VAX stage milestone complete (local mode, then docker/SIMH mode)
- CI workflow changes
- Artifact format changes (`resume.vax.yaml`, transcript parsing, manifest format)

Pre-commit checks are optional by default in this repo workflow.

- Run `.venv/bin/python -m pytest -q`, `.venv/bin/python -m ruff check .`, and
  `.venv/bin/python -m mypy resume_generator tests` when a task or reviewer
  explicitly requests validation.

## No accidental publishing

- GitHub Pages deploy is tag-triggered (`publish` / `publish-*`). Avoid creating/pushing those tags unless you intend to deploy.

## Do-not-break constraints

- Keep Python execution in `.venv/` only.
- Avoid global/system package installs.
- Do not create/push publish tags unless intentionally deploying.
- Preserve evidence workflow for ARPANET changes (manifests/logs referenced in progress docs).

## Expected output shape for implementation work

- Summarize changes by file path.
- Include validation performed (or explicitly state none performed).
- If docs paths changed, update central indexes (`docs/INDEX.md`, relevant domain INDEX files).

## Current VAX/SIMH status (handoff notes)

- Tape (TS11 image) is the working transfer path and is now the default for docker mode.
- Console/FTP transfer code is removed from the active path and archived in `docs/deprecated/transport-archive.md`.
- `vax/bradman.c` was updated for 4.3BSD/K&R C (varargs/stdlib/size_t/void* fallbacks, `_doprnt` + `sys_errlist` stubs).
- Host uuencode decoding is tolerant of trailing garbage in console output.
- Docker image is pinned by digest in code; wait loops avoid fixed sleeps.
