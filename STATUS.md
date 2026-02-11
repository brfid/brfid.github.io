# Project Status

**Last updated:** 2026-02-11

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

**Active path**: KL10 + Serial + FTP (VAX → PDP-10 file transfer)

### Current Blocker
- **PDP-10 boot failure**: KS10 emulator cannot boot ITS or TOPS-20
- Error: "Stop code 7, PC: 000100" (confirmed on both OSes)
- Solution: Switch to KL10 emulator (community-proven for TOPS-20)

### Three-Phase Plan
**Phase 1**: Fix PDP-10 Boot (switch KS10 → KL10 emulator)
**Phase 2**: Serial Tunnel (VAX ↔ PDP-10 direct connection)
**Phase 3**: File Transfer (FTP from VAX to PDP-10)

**Master Plan**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`

### What Works ✅
- VAX/SIMH + 4.3BSD operational
- VAX FTP server validated (Version 4.105, 1986)
- Serial tunnel infrastructure ready
- Docker compose configs ready

### Archived ❌
- IMP chain (HI1 framing mismatch) → `arpanet/archived/`
- Chaosnet Path A (ITS build timeout) → `docs/arpanet/archive/chaosnet/`
- KS10 boot attempts (emulator incompatibility) → `docs/arpanet/archive/ks10/`

### Next Actions
1. Create `arpanet/Dockerfile.pdp10-kl10` (KL10 emulator)
2. Create `arpanet/configs/kl10-install.ini` (TOPS-20 config)
3. Update `docker-compose.vax-pdp10-serial.yml` for KL10
4. Deploy to AWS: `cd test_infra/cdk && cdk deploy`
5. Test PDP-10 boot and TOPS-20 installation
6. See `docs/arpanet/KL10-SERIAL-FTP-PLAN.md` for full timeline

### AWS Infrastructure
- Status: Cleaned up (2026-02-11)
- Cost: $0/hr (no running instances)
- Ready to redeploy for KL10 testing

**Estimated Time**: 6-10 hours on AWS
**Estimated Cost**: ~$0.40-$0.80

## Key References

- **Master Plan**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`
- Next Steps: `docs/arpanet/progress/NEXT-STEPS.md`
- Serial Architecture: `docs/arpanet/SERIAL-TUNNEL.md`
