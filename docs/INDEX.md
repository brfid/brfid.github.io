# Documentation Index

Primary documentation hub for active project docs.

## Start here

1. `../README.md` — cold-start entry point
2. `../CHANGELOG.md` (`[Unreleased]` first, then latest dated entries)
3. This index

Then apply `../AGENTS.md` constraints.

## Active docs

### Core

- `../resume.yaml` — canonical resume source
- `../CHANGELOG.md` — project history and current state
- `../ARCHITECTURE.md` — pipeline design and data contracts
- `../WORKFLOWS.md` — CI/test/publish behavior

### Vintage pipeline

- `vax/INDEX.md` — VAX stage reference (Stage B: bradman.c)
- `integration/INDEX.md` — pipeline integration (stages, constraints, architecture)
- `integration/operations/PEXPECT-PIPELINE-SPEC.md` — implementation spec for pexpect pipeline
- `archive/DEAD-ENDS.md` — retired path registry (screen/telnet, FTP, ARPANET, PDP-10)

### Site

- `../hugo/` — Hugo site root (PaperMod, content, config)

## Historical material

- `archive/` — research notes from exploratory phases (no active guidance)

## Maintenance rule

When adding or updating docs:

1. Update this index.
2. Update the relevant domain index.
3. Update `../CHANGELOG.md` `[Unreleased]` for current-state changes.
4. Prefer editing existing docs over creating near-duplicates.
