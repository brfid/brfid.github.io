# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current checkpoint (read this first)

- Active path: **Chaosnet-direct** (VAX ↔ PDP-10/ITS, no IMPs).
- IMP chain (Phase 2): **Archived** in `arpanet/archived/`. Blocked on KS10 HI1 framing mismatch. Return to later.
- Chaosnet shim code exists (`arpanet/scripts/chaosnet_shim.py`) but is **not yet validated on AWS**.
- PDP-10 needs to be **switched from TOPS-20 to ITS** for Chaosnet support.

Canonical references:
- `STATUS.md`
- `docs/arpanet/progress/NEXT-STEPS.md`
- `docs/arpanet/progress/PATH-A-CHAOSNET-PLAN.md`

Archived IMP blocker analysis:
- `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- `arpanet/archived/README.md`

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
- Chaosnet plan: `docs/arpanet/progress/PATH-A-CHAOSNET-PLAN.md`
- Archived IMP topology: `arpanet/archived/`
- Canonical mismatch analysis: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
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
# Check container status (Chaosnet topology)
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 \
  "cd brfid.github.io && docker compose -f docker-compose.arpanet.chaosnet.yml ps"

# Tear down old IMP containers if still running
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186 \
  "cd brfid.github.io && docker compose -f arpanet/archived/docker-compose.arpanet.phase2.yml down 2>/dev/null; true"
```

### AWS CLI availability

- The remote host may not have AWS CLI installed.
- Use `docker compose` directly on the remote for container operations.
- Use `python3` (not `.venv/bin/python`) on the remote.

## 6) If task touches ARPANET runtime behavior

- Check next actions first: `docs/arpanet/progress/NEXT-STEPS.md`
- The active topology is **Chaosnet-direct** (`docker-compose.arpanet.chaosnet.yml`)
- IMP chain is archived — do not start IMP containers unless explicitly returning to that work

## 7) Essential Commands

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

## 8) Critical Constraints

❌ **Do not:**
- Install Python packages globally (use `.venv/` only)
- Create or push `publish` or `publish-*` tags (unless deploying to GitHub Pages)
- Make broad speculative changes without evidence
- Start IMP containers (archived — use Chaosnet topology)

✅ **Do:**
- Keep changes focused and grounded
- Update `STATUS.md` at significant milestones
- Follow commit cadence guidelines in `AGENTS.md`
- Reference evidence (manifests, logs) for ARPANET work
