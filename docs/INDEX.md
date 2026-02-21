# Documentation Index

Primary documentation hub for active project docs.

## Start here

1. `../README.md` — cold-start entry point (infrastructure boundary, source-of-truth map, quickstart)
2. `../CHANGELOG.md` (`[Unreleased]` first, then latest dated entries)
3. this index

Then apply `../AGENTS.md` constraints.

## Active docs

### Core
- `../resume.yaml` — canonical resume source
- `../CHANGELOG.md` — chronological project history and milestone evidence
- `../ARCHITECTURE.md` — pipeline design, data contracts (`resume.vintage.yaml` schema, console protocol)
- `../resume_generator/` — build implementation
- `../scripts/` — automation helpers
- `../templates/` — rendering templates
- `../WORKFLOWS.md` — CI/test/publish behavior

### Vintage build domains
- `vax/INDEX.md` — VAX docs
- `pdp/INDEX.md` — PDP docs
- `integration/INDEX.md` — integration docs map (mixed current + retained historical evidence)

### AWS/platform
- `aws/INDEX.md` — AWS-facing docs in this repo
- `../aws-*.sh` — minimal lifecycle wrappers
- `edcloud` platform docs (external):
  - `https://github.com/brfid/edcloud/blob/main/README.md`
  - `https://github.com/brfid/edcloud/blob/main/SETUP.md`
  - `https://github.com/brfid/edcloud/blob/main/DESIGN.md`

## Historical material

- `docs/deprecated/` and `docs/legacy/` are retained for traceability.
- Treat them as historical records, not active runbooks.

## Maintenance rule

When adding/updating docs:

1. update this index,
2. update the relevant domain index,
3. update `../CHANGELOG.md` `[Unreleased]` for current-state/priority changes,
4. update dated `../CHANGELOG.md` entries for notable completed milestones,
5. prefer editing existing docs over creating near-duplicates.
