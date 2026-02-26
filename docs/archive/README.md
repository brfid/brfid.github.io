# Research Archive

Historical notes and planning artifacts from the project's exploratory phases.
These files are retained for traceability — none represent current implementation
guidance or active runbooks.

Organized by emulated host type and pipeline phase. Infrastructure details
(IP addresses, EC2 instance IDs) refer to terminated AWS instances from the
research period and have no operational significance.

## Contents

| Directory | What it covers |
|-----------|----------------|
| `vax/` | VAX/VMS reference notes and early debugging docs, superseded by current `docs/vax/` |
| `pdp-11/` | PDP-11 (2.11BSD) research and debugging notes from initial bring-up |
| `pdp-10/` | DEC PDP-10 (TOPS-20) emulation via KL10/KS10 — evaluated, not shipped |
| `arpanet/` | ARPANET IMP and Chaosnet emulation — evaluated, not shipped; pivot documented in pipeline planning |
| `pipeline-planning/` | Reduced evidence core from early pipeline experiments (including false-positive diagnosis records) |

## Dead-end registry

- `DEAD-ENDS.md` — explicit list of retired/blocked approaches vs the active path

## Current active docs

- `../integration/` — pipeline integration runbooks (VAX ↔ PDP-11)
- `../vax/` — VAX operational reference
- `../../README.md` — cold-start entry point
- `../../CHANGELOG.md` — current state and history

## Historical path note

Some archived files intentionally retain pre-archive path strings (for example
`docs/arpanet/...`) as part of the original evidence record. Treat those as
historical references, not active navigation targets.
