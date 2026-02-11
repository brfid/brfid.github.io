# Project Status

**Last updated:** 2024-01-XX (update this timestamp when making changes)

## Current State

### ✅ Completed
- Static resume site generator (Python-based)
- GitHub Pages deployment (tag-triggered: `publish` / `publish-*`)
- VAX/SIMH stage with tape (TS11) transfer path
  - `bradman.c` updated for 4.3BSD/K&R C compatibility
  - Host-side uuencode decoding tolerant of console garbage
  - Docker mode implemented with digest-pinned image
  - Wait loops use polling instead of fixed sleeps
- Archived console/FTP transfer approaches in `docs/project/transport-archive.md`

### 🚧 In Progress
- ARPANET stage (Phase 3) - see `docs/arpanet/progress/NEXT-STEPS.md`

### 📋 Available Next Steps
1. **Landing page polish** - Enhance UX/styling of generated site
2. **ARPANET continuation** - Follow `docs/arpanet/progress/NEXT-STEPS.md`
3. **Testing/CI** - Expand test coverage, add validation workflows
4. **Documentation** - Keep progress tracking current

## Key Files for New Sessions

**Start here:**
1. This file (`STATUS.md`)
2. `README.md`
3. `docs/COLD-START.md`
4. `docs/INDEX.md`

**For ARPANET work:**
- `docs/arpanet/progress/NEXT-STEPS.md`
- `docs/arpanet/progress/PHASE3-PROGRESS.md`
- `docs/arpanet/INDEX.md`

## Critical Constraints

- ✅ Use `.venv/` for all Python commands (do not install globally)
- ✅ Avoid creating/pushing `publish` tags unless deploying
- ✅ Commit at significant milestones only
- ✅ Run validation when requested: pytest, ruff, mypy

## Environment

Python virtualenv: `.venv/` (must be activated for all operations)

```bash
# Activate venv
source .venv/bin/activate

# Run tests (when requested)
python -m pytest -q

# Run linting (when requested)
python -m ruff check .

# Run type checking (when requested)
python -m mypy resume_generator tests
```

## Recent Changes

- VAX tape transfer is primary path (console/FTP archived)
- `bradman.c` K&R C compatibility fixes landed
- Docker SIMH mode operational with pinned image

## ARPANET Stage

**Active path**: Chaosnet-direct (VAX ↔ PDP-10/ITS, no IMPs)

### What works
- Phase 1 validated (single IMP + VAX, 2026-02-07)
- Chaosnet shim scaffold exists (`arpanet/scripts/chaosnet_shim.py`)
- HI1 evidence tooling works (`test_phase2_hi1_framing.py`)

### Current blocker
- PDP-10 runs TOPS-20, needs ITS for Chaosnet support
- Chaosnet shim not yet deployed/validated on AWS
- ITS on SIMH KS10 feasibility not confirmed

### Archived
- IMP chain (Phase 2) archived in `arpanet/archived/`
- Blocked on KS10 HI1 framing mismatch (Ethernet frames vs 1822 leaders)
- See `arpanet/archived/README.md`

### Next actions
1. Tear down IMP containers on AWS (`make aws-teardown-imps`)
2. Research ITS on SIMH KS10 feasibility
3. Deploy Chaosnet-direct topology
4. See `docs/arpanet/progress/NEXT-STEPS.md`
