# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current checkpoint (read this first)

- Active path: **VAX ↔ PDP-10 Serial Tunnel** (Phase 1: serial-over-TCP).
- PDP-10/ITS: **Active** — TOPS-20 via SIMH KS10.
- IMP chain (Phase 2): **Archived** in `arpanet/archived/`.
- Next phase: Chaosnet-on-Serial (after serial tunnel works).
- PDP-10 instance: **Requires working disk image**.

Canonical references:
- `STATUS.md`
- `docs/arpanet/SERIAL-TUNNEL.md`
- `docs/arpanet/progress/NEXT-STEPS.md`

## 1) Read order

1. `README.md`
2. `AGENTS.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/arpanet/INDEX.md` (for ARPANET tasks)

## 2) Source-of-truth pointers

- Current project state: `STATUS.md`
- Active execution path: `docs/arpanet/progress/NEXT-STEPS.md`
- Progress timeline: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Archived IMP topology: `arpanet/archived/`
- Historical transport decisions: `docs/project/transport-archive.md`

## 3) Fast constraints checklist

- Use `.venv/` Python only.
- Do not install globally.
- Do not create/push publish tags unless intentional (`publish`, `publish-*`).
- Prefer evidence-backed changes and preserve manifest/log workflow.

## 4) If task is documentation-related

- Update central indexes when moving/adding docs:
  - `docs/INDEX.md`
  - domain index (example: `docs/arpanet/INDEX.md`)

## 5) AWS Runtime Access

Two t3.micro instances planned (same VPC):

| VM | Role | Status |
|----|------|--------|
| `arpanet-vax` | VAX/4.3BSD builder | **Not yet provisioned** |
| `arpanet-pdp10` | PDP-10/TOPS-20 (serial tunnel) | **Not yet provisioned** |

Old single-VM (tear down):
- **Host**: `ubuntu@34.227.223.186`
- **Teardown**: `make aws-teardown-imps` or terminate instance

SSH key: `~/.ssh/id_ed25519`

## 6) If task touches ARPANET runtime behavior

- Check: `docs/arpanet/SERIAL-TUNNEL.md` and `docs/arpanet/progress/NEXT-STEPS.md`
- Active topology: VAX + PDP-10 via serial tunnel (Phase 1)
- IMP containers are archived — do not start them
- Serial tunnel script: `arpanet/scripts/serial-tunnel.sh`

## 7) Essential Commands

```bash
source .venv/bin/activate
python -m resume_generator
python -m pytest -q
python -m ruff check .
python -m mypy resume_generator tests
```

## 8) Critical Constraints

❌ Do not: install globally, push publish tags, start IMP containers
✅ Do: use `.venv/`, update `STATUS.md` at milestones, follow `AGENTS.md`
