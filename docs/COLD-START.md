# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

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

## 5) If task touches ARPANET runtime behavior

- Check next actions first: `docs/arpanet/progress/NEXT-STEPS.md`
- Confirm latest session context: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Keep guardrails in place (dual-window HI1 evidence where applicable).
