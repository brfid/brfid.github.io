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

**Active path**: VAX ↔ PDP-10 Serial Tunnel (Phase 1: serial-over-TCP)

### What works
- VAX/SIMH + 4.3BSD (proven, builder side)
- Serial tunnel infrastructure (`docker-compose.vax-pdp10-serial.yml`)
- Serial tunnel script (`arpanet/scripts/serial-tunnel.sh`)

### Current state
- Phase 1: Serial tunnel infrastructure created
- Phase 2: Chaosnet-on-Serial (after tunnel works)
- Phase 3: Full Chaosnet Bridge (TCP encapsulation)

### Archived
- IMP chain in `arpanet/archived/` (HI1 framing mismatch)
- PDP-11 path (replaced with PDP-10)

### Next actions
1. Test VAX console connectivity (port 2323)
2. Test PDP-10 console connectivity (port 2326)
3. Start serial tunnel: `./arpanet/scripts/serial-tunnel.sh start`
4. Verify tunnel works: telnet localhost 9000
5. Once tunnel works, move to Phase 2 (Chaosnet-on-Serial)
6. See `docs/arpanet/SERIAL-TUNNEL.md` for full architecture

### Cost
- Two t3.micro: ~$0.02/hr running, $0 stopped
- Old t3.medium: $0.04/hr (terminate after migration)

## Key References

- Serial Tunnel Architecture: `docs/arpanet/SERIAL-TUNNEL.md`
- Chaosnet Shim: `arpanet/scripts/chaosnet_shim.py`
