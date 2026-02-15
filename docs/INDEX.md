# Documentation Index

Central hub for all project documentation.

## Quick Start

New to the project? Start here:

1. **`../README.md`** - Project overview
2. **`COLD-START.md`** - Quick onboarding for new sessions
3. **`../STATUS.md`** - Current project status
4. This index

Then apply repository workflow constraints from `../AGENTS.md`.

## Project Structure

### Core
- **`../resume.yaml`** - Canonical resume source
- **`../resume_generator/`** - Python build package
- **`../templates/`** - Site templates
- **`../scripts/`** - Build/automation scripts
- **`COLD-START.md`** - Quick start guide
- **`../AGENTS.md`** - Repository workflow

### Vintage Systems (VAX ↔ PDP-11)
- **`../vintage/`** - Active VAX/PDP-11 configs
- **`../docker-compose.production.yml`** - Production orchestration (active root compose)
- **`vax/INDEX.md`** - VAX/BSD documentation
- **`pdp/pdp11/`** - PDP-11/2.11BSD systems
- **Scripts**: `vax-console-upload.sh`, `vax-console-build.sh`

### AWS Infrastructure
- **`aws-*.sh`** - Instance management scripts
- **`aws/INDEX.md`** - AWS infrastructure docs

### Legacy / Historical
- **`legacy/arpanet-history/`** - ARPANET IMP research (archived)
- **`legacy/archived/`** - Superseded configurations and test/debug artifacts
  - Archived compose files moved from repo root:
    - `docker-compose.panda-vax.yml`
    - `docker-compose.pdp10-test.yml`
    - `docker-compose.vax-pdp10-serial.yml`
    - `docker-compose.vintage-phase1.yml`
    - `docker-compose.vintage-phase2.yml`
  - Archived debug scripts moved from repo root:
    - `test_ftp_connect.py`
    - `test_packet_debug.py`

## Current Priority

The current priority is **nailing down the VAX → PDP-11 model in AWS**:
- Focus on `STATUS.md` and `COLD-START.md` for current state
- Vintage configs in `vintage/` are actively used
- IMP research preserved in `docs/legacy/` for historical reference

## Deprecated

Old docs moved to `docs/deprecated/` - only check if you need historical context.

## Adding New Documentation

When creating new docs:

1. Add to appropriate section in this index
2. If domain-specific, also add to domain INDEX
3. Update `../STATUS.md` if it represents a milestone
4. Do not create docs that duplicate existing solutions
5. When a problem is solved, update existing docs rather than creating new ones
