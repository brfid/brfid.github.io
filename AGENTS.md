# Agent notes (repo workflow)

Purpose: this file defines agent workflow constraints only.
Setup/quickstart belongs in `README.md`; mutable project memory belongs in `CHANGELOG.md`
under `[Unreleased]`; chronological history belongs in dated `CHANGELOG.md` entries.

## Mission (stable constraints)

- Build and publish a Hugo-based personal site and technical writing portfolio at jockeyholler.net.
- Hugo owns the full site (landing page, blog, resume, portfolio). The vintage pipeline (VAX/PDP-11 via SIMH) remains as an on-demand artifact generator feeding Hugo inputs — not a site generator.
- Blog and portfolio are the primary content surfaces; the vintage pipeline is a technical signal, not the product.
- Prefer clear, evidence-backed updates over broad speculative changes.
- Keep infrastructure orchestration minimal in this repo; lifecycle control belongs to `edcloud` and should be operable from small ARM controller hosts (for example, Pi Zero 2 class devices).

## Start-here order (for new LLM sessions)

`README.md` is the cold-start entry point (infrastructure boundary, source-of-truth map, quickstart, publish tags).

1. `README.md`
2. `CHANGELOG.md` (`[Unreleased]` first, then latest dated entries)
3. `hugo/` (Hugo site root — theme, content, config)
4. `docs/INDEX.md`
5. `docs/integration/INDEX.md` (only if touching vintage pipeline internals)

## Source-of-truth map

- Current mutable state / active queue: `CHANGELOG.md` `[Unreleased]`
- Change history / milestone evidence: dated `CHANGELOG.md` entries
- Documentation hub: `docs/INDEX.md`
- Integration active path + spec: `docs/integration/INDEX.md`
- Implementation spec (pexpect pipeline): `docs/integration/operations/PEXPECT-PIPELINE-SPEC.md`
- Explicit retired/blocked path registry: `docs/archive/DEAD-ENDS.md`

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
7. Do not record routine blog content authoring/editing/import work in `CHANGELOG.md`;
   reserve changelog updates for repo workflow, infrastructure, tooling, and runtime-status changes.

## Local dev

Run `hugo server --source hugo` from the repo root to preview locally.
The operator node is a Raspberry Pi — the server is accessible in-browser on
that machine. No staging environment or remote preview URL is needed.

## Virtualenv-only

- Use the repo-local venv at `.venv/` for all Python commands.
- Do not install anything globally or modify system Python.

## Commit cadence

Commit at significant milestones so the history stays readable and bisectable. Examples:

- Hugo scaffold complete (theme, config, first content)
- Landing page / design milestone complete
- New post published or portfolio entry added
- Deploy workflow changes (Hugo build step, Pages config)
- Vintage pipeline changes (SIMH stages, artifact format)

Pre-commit checks are optional by default in this repo workflow.

- Run `.venv/bin/python -m pytest -q`, `.venv/bin/python -m ruff check resume_generator`, and
  `.venv/bin/python -m mypy resume_generator host_logging tests` when a task or reviewer
  explicitly requests validation.
- When a milestone completes, update `CHANGELOG.md` in the same change set.

## Git discipline (public-repo baseline)

- Keep `main` linear and readable: small, intention-revealing commits; no WIP commits.
- Prefer additive fixes over history rewrites; rewrite shared `main` history only when
  explicitly requested by the operator.
- Keep local and remote synchronized after each milestone (`git push origin main`,
  then verify `main...origin/main` is clean).
- Treat deploy tags as operational triggers, not release history; maintain a short rolling
  set of timestamp tags and keep milestone/version tags intentionally.
- Before pushing, check for accidental secret material in changed files and avoid committing
  generated artifacts (`site/`, `build/`, `hugo/public/`, `.venv/`).

## No accidental publishing

- GitHub Pages deploy is tag-triggered (`publish-fast-*`, `publish-vintage-*`). Avoid creating/pushing those tags unless you intend to deploy.

## Do-not-break constraints

- Keep Python execution in `.venv/` only.
- Avoid global/system package installs.
- Do not create/push publish tags unless intentionally deploying.
- Do not reintroduce screen/telnet/sleep-based console orchestration; the pexpect approach supersedes it.

## Expected output shape for implementation work

- Summarize changes by file path.
- Include validation performed (or explicitly state none performed).
- If docs paths changed, update central indexes (`docs/INDEX.md`, relevant domain INDEX files).

## Runtime-status boundary

- Keep long-lived constraints here; record changing implementation status in
  `CHANGELOG.md` `[Unreleased]`.
- Prefer referencing current paths in code/docs (for example `vintage/machines/vax/bradman.c`).
