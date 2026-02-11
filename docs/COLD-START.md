# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current checkpoint (read this first)

- **Active path**: KL10 + Serial + FTP (3-phase plan)
- **Current blocker**: PDP-10 cannot boot (KS10 emulator incompatible)
- **Solution**: Switch to KL10 emulator (community-proven for TOPS-20)
- **Next action**: Create KL10 Dockerfile and configs
- **Testing**: All on AWS (Raspberry Pi incompatible)

**Canonical references**:
- `STATUS.md`
- `docs/arpanet/KL10-SERIAL-FTP-PLAN.md` (master plan)
- `docs/arpanet/progress/NEXT-STEPS.md` (concrete steps)

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

**Status**: All instances terminated (2026-02-11)

**Previous instance** (ArpanetTestStack):
- Destroyed due to ITS build blocker on Path A (Chaosnet)
- No running AWS resources
- Cost: $0/hr

**To redeploy** (when needed):
```bash
cd test_infra/cdk
source ../../.venv/bin/activate
cdk deploy
```

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
