# Agent notes (repo workflow)

Purpose: this file defines agent workflow constraints only.
Setup/quickstart belongs in `README.md`; mutable project memory belongs in `CHANGELOG.md`
under `[Unreleased]`; chronological history belongs in dated `CHANGELOG.md` entries.

## Mission (stable constraints)

- Build and publish a static resume site, with optional vintage/ARPANET stages used as a technical signal.
- Keep build outputs reproducible and historically grounded where intended (vintage/SIMH + ARPANET tracks).
- Prefer clear, evidence-backed updates over broad speculative changes.
- Keep infrastructure orchestration minimal in this repo; lifecycle control belongs to `edcloud` and should be operable from small ARM controller hosts (for example, Pi Zero 2 class devices).

## Start-here order (for new LLM sessions)

`README.md` is the cold-start entry point (infrastructure boundary, source-of-truth map, quickstart, publish tags).

1. `README.md`
2. `CHANGELOG.md` (`[Unreleased]` first, then latest dated entries)
3. `docs/INDEX.md`
4. `docs/integration/INDEX.md` (if touching integration/ARPANET history)

## Source-of-truth map

- Current mutable state / active queue: `CHANGELOG.md` `[Unreleased]`
- Change history / milestone evidence: dated `CHANGELOG.md` entries
- Documentation hub: `docs/INDEX.md`
- Integration active path + known-good evidence: `docs/integration/INDEX.md`
- Integration history log (retained, not active): `docs/integration/progress/NEXT-STEPS.md`
- Integration progress timeline (retained): `docs/integration/progress/PHASE3-PROGRESS.md`
- Historical transport decisions: `docs/deprecated/transport-archive.md`

Do not duplicate mutable status in this file; update `CHANGELOG.md` (`[Unreleased]`) instead.

## Changelog memory model

Use Keep a Changelog structure with one repo convention:

- `## [Unreleased]` is the LLM working-memory section and uses custom subcategories
  in this exact order:
  1. `Current State`
  2. `Active Priorities`
  3. `In Progress`
  4. `Blocked`
  5. `Decisions Needed`
  6. `Recently Completed`
- Keep every subcategory present; if empty, use `- None.`.
- Dated entries (`## [YYYY-MM-DD]`) keep normal Keep a Changelog categories
  (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`).

Update rules:

1. On start/end of a task, update `In Progress` and `Recently Completed`.
2. On new queued work, update `Active Priorities`.
3. On external dependency or waiting condition, update `Blocked`.
4. On user choice needed, update `Decisions Needed`.
5. On architecture/runtime truth changes, update `Current State`.
6. On milestone/date cut, move `Recently Completed` items into a dated entry and
   classify under standard Keep a Changelog categories.

## Virtualenv-only

- Use the repo-local venv at `.venv/` for all Python commands.
- Do not install anything globally or modify system Python.

## Commit cadence

Commit at significant milestones so the history stays readable and bisectable. Examples:

- Landing page / UX milestone complete
- Vintage stage milestone complete (local mode, then docker/SIMH mode)
- CI workflow changes
- Artifact format changes (`resume.vintage.yaml`, transcript parsing, manifest format)

Pre-commit checks are optional by default in this repo workflow.

- Run `.venv/bin/python -m pytest -q`, `.venv/bin/python -m ruff check resume_generator`, and
  `.venv/bin/python -m mypy resume_generator host_logging tests` when a task or reviewer
  explicitly requests validation.
- When a milestone completes, update `CHANGELOG.md` in the same change set.

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

## Runtime-status boundary

- Keep long-lived constraints here; record changing implementation status in
  `CHANGELOG.md` `[Unreleased]`.
- Prefer referencing current paths in code/docs (for example `vintage/machines/vax/bradman.c`).
