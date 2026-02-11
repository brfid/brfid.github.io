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

**Active path**: Direct transfer (VAX/4.3BSD ↔ PDP-11/2.11BSD, two t3.micro VMs)

### What works
- VAX/SIMH + 4.3BSD (builder side — proven, in production)
- bradman.c compiles under K&R C (should work on 2.11BSD as-is)

### Current state
- Two t3.micro VMs: **not yet provisioned**
- PDP-11/2.11BSD: need disk image and Dockerfile
- Transfer method: TBD (FTP, serial, or UUCP)
- Old t3.medium: **tear down pending**

### Archived
- IMP chain in `arpanet/archived/` (HI1 framing mismatch)
- PDP-10/ITS path dropped (emulator complexity)
- Chaosnet plan superseded (no longer needed without ITS)

### Next actions
1. Tear down old t3.medium
2. Provision two t3.micro instances
3. Find/build 2.11BSD disk image for SIMH PDP-11
4. Create PDP-11 Dockerfile and SIMH config
5. Test bradman.c compilation on 2.11BSD
6. Implement transfer (FTP or serial)
7. See `docs/arpanet/progress/NEXT-STEPS.md`

### Cost
- Two t3.micro: ~$0.02/hr running, $0 stopped
- Old t3.medium: $0.04/hr (terminate after migration)
