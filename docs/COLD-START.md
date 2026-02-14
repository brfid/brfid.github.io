# Cold Start Guide (LLM / New Operator)

Use this page when starting from zero context.

## 0) Current State (read this first)

**Date**: 2026-02-14
**Status**: ✅ COMPLETE - Uuencode console transfer system fully operational

- **AWS Infrastructure**: ✅ DEPLOYED (2x t3.micro)
- **Latest Achievement**: End-to-end VAX → PDP-11 uuencode transfer working
- **Deployment**: publish-vax-uuencode-v3 (successful)
- **Architecture**: VAX → uuencode → console → PDP-11 (discrete machines, no shared data)
- **Cost**: ~$17.90/month running, ~$2/month stopped (storage only)
- **Fixes Applied**:
  - ✅ EFS builds directory created in CDK user_data
  - ✅ Screen session auto-recovery when telnet times out
  - ✅ Build logs merged chronologically (VAX, COURIER, GITHUB)

**Canonical references**:
- `STATUS.md` - Overall project status
- `docs/YAML-ENHANCEMENT-PLAN.md` - YAML parser enhancement roadmap
- `docs/integration/TAPE-TRANSFER-VALIDATION-2026-02-13.md` - Tape transfer proof
- `PRODUCTION-DEPLOYMENT.md` - Complete deployment guide (AWS)

**Quick AWS management**:
```bash
./aws-status.sh  # Check instance state and costs
./aws-stop.sh    # Stop instances (saves $15/month, keeps data)
./aws-start.sh   # Start instances (shows new IPs)
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
- Historical transport decisions: `docs/project/transport-archive.md`
- PDP-10 experiments: `docs/pdp/pdp10/`

## 3) Fast constraints checklist

- Use `.venv/` Python only.
- Do not install globally.
- Do not create/push publish tags unless intentional (`publish`, `publish-*`).
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

## 9) What Changed Recently (2026-02-13)

1. **IMP Phase Archived**: Protocol incompatibility (Ethernet/TCP-IP vs ARPANET 1822)
   - All IMP materials moved to `docs/integration/archive/`
   - Simplified to direct VAX ↔ PDP-11 TCP/IP

2. **Production Infrastructure Deployed**:
   - 2x t3.micro instances (VAX + PDP-11)
   - Shared EFS logging at `/mnt/arpanet-logs/`
   - Simple management scripts at repo root

3. **PDP-11 Added**:
   - Replaced PDP-10 (console automation issues)
   - 2.11BSD pre-built image
   - Native Ethernet support

## 10) Important Notes

- **AWS credentials**: Account 972626128180, region us-east-1
- **SSH key**: `~/.ssh/arpanet-temp.pem`
- **EFS ID**: `fs-03cd0abbb728b4ad8`
- **Network**: Docker bridge `172.20.0.0/16`
- **Data safety**: Stop/start preserves all data (EFS + EBS)
- **IMPs**: Archived but can be restored if needed

## 11) Current Priorities (2026-02-13)

**Phase 1: YAML Parser Enhancement** (IN PROGRESS)
- Goal: Enhance VAX C parser to handle 95% of YAML syntax
- Remove Python preprocessing dependency
- Timeline: 8-9 hours estimated
- See: `docs/YAML-ENHANCEMENT-PLAN.md`

**Phase 2: GitHub Workflow Simplification** (COMPLETED ✅)
- Removed ARPANET Phase 2 (IMPs no longer needed)
- Simplified to VAX-only builds
- Enhanced build logging
- See: `.github/workflows/deploy.yml`

**Phase 3: Tape Transfer Integration** (FUTURE)
- Proven working: VAX ↔ PDP-11 via SIMH tape
- Can integrate into pipeline later
- See: `docs/integration/TAPE-TRANSFER-VALIDATION-2026-02-13.md`

---

**Recent Achievements** (2026-02-13):
- ✅ Tape transfer validated end-to-end
- ✅ SIMH TAP parser created
- ✅ GitHub workflow simplified
- ✅ YAML enhancement plan created
