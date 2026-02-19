# Documentation Index

Primary documentation hub for active project docs.

## Start here

1. `../README.md`
2. `COLD-START.md`
3. `../STATUS.md`
4. this index

Then apply `../AGENTS.md` constraints.

## Active docs

### Core
- `../resume.yaml` — canonical resume source
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
3. update `../STATUS.md` if behavior/architecture changed,
4. prefer editing existing docs over creating near-duplicates.
