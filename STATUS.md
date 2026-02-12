# Project Status

**Last updated:** 2026-02-12

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

### Current Status (2026-02-12)
- **PDP-10 installation automation attempted** - Multiple approaches tested
- ✅ SIMH configuration errors fixed (unit number syntax)
- ✅ Automation method proven (screen + command stuffing works)
- ❌ TOPS-20 V4.1: Boot loop bug (WRCSTM instruction issue)
- ⚠️ TOPS-20 V7.0: Cornwell SIMH parameter incompatibilities
- ⚠️ KLH10: Execution errors with Docker image
- **Recommendation**: Manual installation (15-30 min) or use TOPS-10
- **See**: `docs/arpanet/PDP10-INSTALLATION-ATTEMPTS-2026-02-12.md`

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
**Option A (Recommended)**: Manual TOPS-20 installation
1. Start container interactively on AWS or locally
2. Type `/L` and `/G143` at MTBOOT> prompt
3. Complete installation (15-30 min)
4. Save disk image for reuse

**Option B**: Try TOPS-10 instead (better compatibility)
1. Download TOPS-10 installation tape
2. Use similar process to TOPS-20
3. Likely avoids boot loop issues

**Option C**: Continue debugging automation
1. Fix Cornwell SIMH parameter compatibility
2. Or debug KLH10 execution issues
3. Time investment: 1-2 hours more

### AWS Infrastructure
- Status: Instance running (2026-02-12)
- Instance: 34.202.231.2 (i-063975b939603d451)
- Type: t3.medium
- Cost: ~$0.04/hr
- **Action needed**: Destroy when done (`cd test_infra/cdk && cdk destroy --force`)

**Time invested**: ~3 hours
**Cost so far**: ~$0.12

## Key References

- **Master Plan**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`
- Next Steps: `docs/arpanet/progress/NEXT-STEPS.md`
- Serial Architecture: `docs/arpanet/SERIAL-TUNNEL.md`
