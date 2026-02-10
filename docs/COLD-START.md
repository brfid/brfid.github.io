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
