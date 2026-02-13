# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current checkpoint (read this first)

- **Active path**: Panda KLH10 TOPS-20 bring-up (direct TCP/IP path)
- **Current known-good**: KLH10 boots to `BOOT V11.0(315)` with `RH20.RP07.1`
- **Current blocker**: BOOT control-plane ingress is unstable (no proven `@` prompt yet)
- **Critical fix already landed**: `mount dsk0 ...` → `devmount dsk0 ...`
- **Next action**: capture one successful manual `docker attach` transcript to `@`, then codify into automation
- **Testing**: AWS-first runtime validation

**Canonical references**:
- `STATUS.md`
- `docs/arpanet/progress/NEXT-STEPS.md` (concrete steps)
- `docs/arpanet/INDEX.md` (active vs archived ARPANET docs)
- `docs/arpanet/KL10-SERIAL-FTP-PLAN.md` (fallback/historical strategy context)

## 1) Read order

1. `README.md`
2. `docs/COLD-START.md`
3. `STATUS.md`
4. `docs/INDEX.md`
5. `docs/arpanet/INDEX.md` (for ARPANET tasks)

Then apply repository workflow constraints from `AGENTS.md`.

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

**Status**: Active Panda runtime used for validation (see `STATUS.md` / `docs/arpanet/progress/NEXT-STEPS.md` for latest instance/IP)

**Note**:
- Instance details and costs can change between sessions.
- Treat `STATUS.md` + `docs/arpanet/progress/NEXT-STEPS.md` as canonical for current live host information.

**To redeploy** (when needed):
```bash
cd test_infra/cdk
source ../../.venv/bin/activate
cdk deploy
```

## 6) If task touches ARPANET runtime behavior

- Check: `docs/arpanet/progress/NEXT-STEPS.md` first, then Panda docs
- Active topology for current blocker: Panda VAX + PDP-10 (`docker-compose.panda-vax.yml`)
- IMP containers are archived — do not start them
- Serial tunnel docs are historical context, not the current execution path

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
