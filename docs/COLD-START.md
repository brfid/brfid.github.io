# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current State (read this first)

**Date**: 2026-02-14
**Status**: ✅ GitHub Actions + edcloud lifecycle stable (activate → run → deactivate)

- **Infrastructure**: ✅ DEPLOYED (edcloud single host: t3a.medium with Docker)
- **Architecture**: VAX + PDP-11 containers on single host, shared volume for transfer
- **VAX Solution**: Console I/O via screen + telnet (runs INSIDE BSD, not container!)
- **Scripts**: `vax-console-upload.sh`, `vax-console-build.sh`, `vax-build-and-encode.sh`
- **Verification**: Vintage K&R C compilation verified inside 4.3BSD
- **Workflow**: `.github/workflows/deploy.yml` uses edcloud activation/deactivation
- **Logging**: `GITHUB.log` includes edcloud lifecycle markers
- **Cost**: ~$11/month at 4hrs/day, ~$6.40/month stopped (storage only)

**Canonical references**:
- `STATUS.md` - Overall project status
- `docs/INDEX.md` - Documentation hub
- `edcloud/MIGRATION.md` - Migration from old AWS stack (completed 2026-02-14)
- `docs/deprecated/` - Old docs (historical context only)

**Quick infrastructure management**:
```bash
./aws-status.sh  # Check edcloud status, Tailscale IP, costs
./aws-stop.sh    # Stop edcloud (saves compute cost, keeps data)
./aws-start.sh   # Start edcloud (shows new public IP)
```

## 1) Read order

1. `README.md`
2. `docs/COLD-START.md` (this file)
3. `STATUS.md`
4. `docs/INDEX.md`
5. Machine-specific INDEX (e.g., `docs/vax/INDEX.md`, `docs/pdp/INDEX.md`, `docs/integration/INDEX.md`)

Then apply repository workflow constraints from `AGENTS.md`.

## 2) Source-of-truth pointers

**Project state**:
- Current status: `STATUS.md`
- Next actions: `docs/integration/progress/NEXT-STEPS.md`
- Production deployment: `PRODUCTION-DEPLOYMENT.md`

**AWS Infrastructure**:
- Stack code: `infra/cdk/arpanet_production_stack.py`
- Management scripts: `aws-*.sh` (repo root)
- Deployment guide: `docs/aws/INDEX.md`

**Architecture**:
- Simplified: VAX + PDP-11 direct TCP/IP (no IMPs)
- IMP phase archived: `docs/integration/archive/imp-phase/`
- Docker compose: `docker-compose.production.yml`

**Historical references**:
- Archived IMP topology: `docs/integration/archive/imp-phase/`
- Historical transport decisions: `docs/deprecated/transport-archive.md`
- PDP-10 experiments: `docs/pdp/pdp10/`

## 3) Fast constraints checklist

- Use `.venv/` Python only.
- Do not install globally.
- Do not create/push publish tags unless intentional (`publish*`, `publish-fast*`, `publish-vintage*`).
- Prefer evidence-backed changes and preserve manifest/log workflow.
- AWS instances can be stopped/started without data loss (EFS + EBS persist).

## 4) If task is documentation-related

- Update central indexes when moving/adding docs:
  - `docs/INDEX.md`
  - domain index (example: `docs/vax/INDEX.md`, `docs/pdp/INDEX.md`)
- Keep `STATUS.md` current
- Document significant changes in `docs/integration/progress/`

## 5) If task is AWS-related

**Check current state first**:
```bash
./aws-status.sh
```

**Access instances**:
```bash
# Get IPs from status script output
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<pdp11-ip>
```

**Console access**:
```bash
telnet <vax-ip> 2323    # VAX console
telnet <pdp11-ip> 2327  # PDP-11 console
```

**Stop when done** (saves money):
```bash
./aws-stop.sh  # Keeps all data, saves $15/month
```

## 6) Current Architecture

```
┌─────────────────────────────────────────────┐
│         Docker Bridge 172.20.0.0/16         │
│                                              │
│   ┌──────────────┐       ┌──────────────┐   │
│   │  VAX/BSD     │       │  PDP-11/BSD  │   │
│   │  172.20.0.10 │◄─────►│  172.20.0.50 │   │
│   │  de0         │  TCP  │  xq0         │   │
│   │  Port 2323   │  /IP  │  Port 2327   │   │
│   └──────────────┘       └──────────────┘   │
│                                              │
└─────────────────────────────────────────────┘
                     │
                     ▼
           /mnt/arpanet-logs/ (EFS)
```

## 7) Key Files

**Management scripts** (repo root):
- `aws-status.sh` - Check instances
- `aws-stop.sh` - Stop instances
- `aws-start.sh` - Start instances

**Infrastructure**:
- `infra/cdk/arpanet_production_stack.py` - AWS CDK stack
- `docker-compose.production.yml` - Container orchestration

**Documentation**:
- `STATUS.md` - Current project status
- `PRODUCTION-DEPLOYMENT.md` - Full deployment guide
- `docs/integration/PRODUCTION-STATUS-2026-02-13.md` - Deployment report
- `docs/integration/progress/NEXT-STEPS.md` - Next actions

**Archives**:
- `docs/integration/archive/` - Historical integration approaches

## 8) Common Tasks

### Check AWS status
```bash
./aws-status.sh
```

### Access VAX
```bash
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<vax-ip>
telnet <vax-ip> 2323  # Console
```

### Access PDP-11
```bash
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<pdp11-ip>
telnet <pdp11-ip> 2327  # Console
```

### Check logs
```bash
# On either instance:
tail -f /mnt/arpanet-logs/vax/boot.log
tail -f /mnt/arpanet-logs/pdp11/boot.log
du -sh /mnt/arpanet-logs/*
```

### Manage containers
```bash
# On either instance:
cd ~
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f
docker-compose -f docker-compose.production.yml restart vax
```

### Save money
```bash
./aws-stop.sh  # $17/month → $2/month (storage only)
```

## 9) What Changed Recently

**2026-02-14: Migration to edcloud backend**
- Replaced ArpanetProductionStack (2x t3.micro) with single edcloud host (t3a.medium)
- Both VAX + PDP-11 now run as containers on single Docker host
- Shared volume (`build-shared`) replaces EFS for artifact transfer
- Console-based transfer preserved for historical fidelity
- Cost reduction: $17.90/mo → $11/mo at 4hrs/day, $6.40/mo stopped
- See `edcloud/MIGRATION.md` for full migration details

**2026-02-13: IMP Phase Archived and Production Deployed**

1. **IMP Phase Archived**: Protocol incompatibility (Ethernet/TCP-IP vs ARPANET 1822)
   - All IMP materials moved to `docs/integration/archive/`
   - Simplified to direct VAX ↔ PDP-11 TCP/IP

2. **Production Infrastructure Deployed** (now superseded by edcloud):
   - 2x t3.micro instances (VAX + PDP-11)
   - Shared EFS logging at `/mnt/arpanet-logs/`
   - Simple management scripts at repo root

3. **PDP-11 Added**:
   - Replaced PDP-10 (console automation issues)
   - 2.11BSD pre-built image
   - Native Ethernet support

## 10) Important Notes

- **AWS credentials**: Account 972626128180, region us-east-1
- **edcloud instance**: i-01798b99c71dd93a5 (t3a.medium, 80GB gp3)
- **Tailscale**: 100.127.208.71 (hostname "edcloud")
- **SSH access**: EC2 Instance Connect (temp) + authorized_keys (permanent)
- **Network**: Docker bridge `172.20.0.0/16` (VAX .10, PDP-11 .50)
- **Data safety**: Stop/start preserves EBS volume - no data loss
- **Old stack**: ArpanetProductionStack destroyed 2026-02-14 (EFS fs-03cd0abbb728b4ad8 deleted)

## 11) Current Priorities

**Phase 1: VAX Console Build Pipeline** (SOLVED ✅)
- Solution: Console I/O via screen + telnet
- Scripts created: `vax-console-upload.sh`, `vax-console-build.sh`
- Verification: Vintage K&R C compilation works inside BSD
- Status: Integrated into deploy workflow

**Phase 2: GitHub↔AWS Lifecycle Reliability** (COMPLETE ✅)
- AWS activation consolidated into one workflow step
- AWS deactivation consolidated with `always()` + `wait instance-stopped`
- Lifecycle markers emitted to `GITHUB.log`:
  - `AWS_ACTIVATE_BEGIN`, `AWS_ACTIVATE_READY`, `AWS_ACTIVATE_FAILED`
  - `AWS_DEACTIVATE_BEGIN`, `AWS_DEACTIVATE_COMPLETE`

**Publish tags (current canonical)**:
- Fast local: `publish`, `publish-fast`, `publish-fast-*`
- Distributed vintage: `publish-vintage`, `publish-vintage-*`
- Legacy aliases still accepted: `publish-vax*`, `publish-docker*`

**Phase 3: End-to-End Testing** (PENDING)
- Full VAX → PDP-11 workflow
- Verify logs reflect vintage tool usage
- Deploy and validate

---

**Recent Achievements**:
- ✅ VAX console build pipeline solved (solution exists)
- ✅ Vintage K&R C verified working inside 4.3BSD
- ✅ Old confusing docs archived to `docs/deprecated/`
- ✅ Documentation cleaned up for clarity
