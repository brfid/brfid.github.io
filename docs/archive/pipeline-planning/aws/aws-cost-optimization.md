# AWS Cost Baseline (Current edcloud Model)

## Scope

This document tracks costs for the **current** deployment model:

- Single EC2 host managed by `edcloud`
- `brfid.github.io` drives lifecycle with `aws-start.sh`, `aws-stop.sh`, `aws-status.sh`
- VAX + PDP-11 containers run together on that one host

## Current Baseline

From the current `aws-status.sh` estimate (4 hours/day runtime):

- Compute: `$4.51/month`
- Storage: `$6.40/month`
- Total: `$10.91/month`

When stopped:

- Storage only: about `$6.40/month`

## Cost Controls In Active Use

1. Stop when idle:

```bash
./aws-stop.sh
```

2. Start only for active work/publish:

```bash
./aws-start.sh
```

3. Check status + estimate anytime:

```bash
./aws-status.sh
```

4. Keep infra policy centralized in `edcloud`:
   - Instance shape/volume decisions
   - Snapshot + restore policy
   - Host baseline toolchain

## Optimization Levers

1. Runtime hours per day:
   - Largest immediate lever on compute spend.
2. Instance size tuning in `edcloud`:
   - Reduce only after validating VAX/PDP-11 build stability.
3. EBS footprint management:
   - Keep only volumes required for reproducibility + recovery.

## Historical Notes

- The prior two-host CDK/EFS model in this repo was retired on **2026-02-14**.
- Historical references are retained in:
  - `PRODUCTION-DEPLOYMENT.md` (deprecated historical guide)
  - `docs/integration/PRODUCTION-STATUS-2026-02-13.md`
