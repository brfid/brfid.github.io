# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current checkpoint (read this first)

- Active path: **Chaosnet-direct** (VAX ↔ PDP-10/ITS, two separate t3.micro VMs).
- IMP chain (Phase 2): **Archived** in `arpanet/archived/`. Blocked on KS10 HI1 framing mismatch.
- PDP-10 needs **ITS** (not TOPS-20) for Chaosnet support. ITS runtime not yet validated.
- Chaosnet shim code exists (`arpanet/scripts/chaosnet_shim.py`) but is **not yet deployed**.

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

## 5) AWS Runtime Access

Two t3.micro instances in the same VPC (pending provisioning):

| VM | Role | Instance type | Status |
|----|------|--------------|--------|
| `arpanet-vax` | VAX/4.3BSD (SIMH) | t3.micro | **Not yet provisioned** |
| `arpanet-pdp10` | PDP-10/ITS (KLH10 or SIMH) | t3.micro | **Not yet provisioned** |

Old single-VM (may still be running — tear down):
- **Host**: `ubuntu@34.227.223.186`
- **Teardown**: `make aws-teardown-imps` or terminate instance after new VMs are up

SSH key for all instances: `~/.ssh/id_ed25519`

### Once provisioned, update this section with:
- VAX VM public IP
- PDP-10 VM public IP
- VPC private IPs (for Chaosnet traffic)

## 6) If task touches ARPANET runtime behavior

- Check next actions first: `docs/arpanet/progress/NEXT-STEPS.md`
- Active topology is **Chaosnet-direct** (two VMs, no IMPs)
- IMP containers are archived — do not start them

## 7) Essential Commands

```bash
source .venv/bin/activate
python -m resume_generator
python -m pytest -q
python -m ruff check .
python -m mypy resume_generator tests
```

## 8) Critical Constraints

❌ **Do not:**
- Install Python packages globally
- Create/push publish tags unless deploying
- Start IMP containers (archived)

✅ **Do:**
- Keep changes focused and evidence-backed
- Update `STATUS.md` at milestones
- Follow `AGENTS.md` commit cadence
