# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current checkpoint (read this first)

- Branch state: **Branch B active** (Branch A closed for current KS10 runtime profile).
- Link-layer guardrails: **green** in Session 31 baseline (`final_exit=0`, `bad_magic_total_delta=0`).
- Active blocker (reset): **KS10 `IMP` protocol-stack mismatch** with IMP2 HI1 expectations in current runtime profile.
- Branch B planning priority (current):
  1. **Path A: Chaosnet-first ITS-compatible path**
  2. **Path D fallback: VAX/IMP transfer proof with endpoint compatible with HI1 contract**
  3. Keep Path B/C as lower-priority exploratory options.

Canonical analysis handoff:
- `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`

Primary references:
- `STATUS.md`
- `docs/arpanet/progress/NEXT-STEPS.md`
- `docs/arpanet/progress/PHASE3-PROGRESS.md`

## 1) Read order

1. `README.md`
2. `AGENTS.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/arpanet/INDEX.md` (for ARPANET tasks)

## 2) Source-of-truth pointers

- Current project state: `STATUS.md`
- ARPANET active execution path: `docs/arpanet/progress/NEXT-STEPS.md`
- ARPANET progress timeline: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Current Branch A closure artifact: `build/arpanet/analysis/session30-its-command-matrix.log`
- Current Branch B baseline artifact: `build/arpanet/analysis/hi1-dual-window-branchB-baseline-session31.json`
- Canonical mismatch analysis handoff: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- Historical transport decisions: `docs/project/transport-archive.md`

## 3) Fast constraints checklist

- Use `.venv/` Python only.
- Do not install globally.
- Do not create/push publish tags unless intentional (`publish`, `publish-*`).
- Prefer evidence-backed changes and preserve ARPANET manifest/log workflow.

## 4) If task is documentation-related

- Update central indexes when moving/adding docs:
  - `docs/INDEX.md`
  - domain index (example: `docs/arpanet/INDEX.md`)

## 5) AWS Runtime Access (IMPORTANT)

For ARPANET runtime validation, the active stack runs on AWS:

- **Host**: `ubuntu@34.227.223.186` (i-0568f075e84bf24dd)
- **SSH Key**: `~/.ssh/id_ed25519`
- **Access**: `ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186`
- **Workspace**: `/home/ubuntu/brfid.github.io`

### Quick validation commands

```bash
# Check container status
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 "cd brfid.github.io && docker compose -f docker-compose.arpanet.phase2.yml ps"

# Check shim health
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 "cd brfid.github.io && docker logs arpanet-hi1shim --tail 5"

# Run dual-window gate
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 "cd brfid.github.io && python3 test_infra/scripts/run_hi1_gate_remote.py --dual-window"
```

### AWS CLI availability

- The remote host may not have AWS CLI installed.
- Use `docker compose` directly on the remote for container operations.
- Use `python3` (not `.venv/bin/python`) on the remote.

## 6) If task touches ARPANET runtime behavior

- Check next actions first: `docs/arpanet/progress/NEXT-STEPS.md`
- Confirm latest session context: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Keep guardrails in place (dual-window HI1 evidence where applicable).

# Cold Start Guide

Quick onboarding for new LLM sessions working on this repository.

## Reading Order

1. **`STATUS.md`** - Current project snapshot
2. This file (`docs/COLD-START.md`)
3. **`README.md`** - Project overview
4. **`docs/INDEX.md`** - Documentation hub
5. **`docs/arpanet/INDEX.md`** - If working on ARPANET stage

## Quick Context

This repo builds a static resume site with optional retro computing stages:

- **Modern path:** Python generator → static HTML
- **VAX/SIMH path:** Transfer via tape (TS11), compile `bradman.c` on 4.3BSD
- **ARPANET path:** (Phase 3 in progress) - see `docs/arpanet/progress/NEXT-STEPS.md`

## Essential Commands

```bash
# Activate virtualenv (REQUIRED for all Python work)
source .venv/bin/activate

# Build site locally
python -m resume_generator

# Run validation (when requested)
python -m pytest -q
python -m ruff check .
python -m mypy resume_generator tests
```

## Critical Constraints

❌ **Do not:**
- Install Python packages globally (use `.venv/` only)
- Create or push `publish` or `publish-*` tags (unless deploying to GitHub Pages)
- Make broad speculative changes without evidence

✅ **Do:**
- Keep changes focused and grounded
- Update `STATUS.md` at significant milestones
- Follow commit cadence guidelines in `AGENTS.md`
- Reference evidence (manifests, logs) for ARPANET work

## Current VAX/SIMH Status

- **Working transfer path:** Tape (TS11 image) via Docker SIMH
- **Archived approaches:** Console/FTP (see `docs/project/transport-archive.md`)
- **Code status:** `bradman.c` updated for 4.3BSD/K&R C compatibility
- **Docker mode:** Pinned by digest, uses polling waits

## Where to Start

**For general work:**
- Check `STATUS.md` "Available Next Steps" section

**For ARPANET work:**
- Start at `docs/arpanet/progress/NEXT-STEPS.md`
- Track progress in `docs/arpanet/progress/PHASE3-PROGRESS.md`

**For VAX/SIMH work:**
- Current implementation is in working state
- See `vax/` directory for scripts and `bradman.c`
- Docker mode is primary path

## Documentation Updates

When modifying docs:
- Update `docs/INDEX.md` if adding/moving major doc files
- Update domain INDEX files (`docs/arpanet/INDEX.md`, etc.) for domain-specific changes
- Keep `STATUS.md` current with project state
