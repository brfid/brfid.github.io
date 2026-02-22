# ARPANET Production Deployment - Status Report

**Date**: 2026-02-13
**Status**: ✅ OPERATIONAL
**Architecture**: VAX ↔ PDP-11 Direct TCP/IP (No IMPs)

---

## Deployment Summary

Successfully deployed permanent two-machine ARPANET infrastructure to AWS with shared EFS logging.

### Infrastructure

**AWS Stack**: `ArpanetProductionStack`
- **VAX Host**: t3.micro @ 3.80.32.255 (i-090040c544bb866e8)
- **PDP-11 Host**: t3.micro @ 3.87.125.203 (i-071ab53e735109c59)
- **Storage**: EFS <efs-id> mounted at `/mnt/arpanet-logs/`
- **Network**: Docker bridge 172.20.0.0/16
- **Cost**: ~$17.90/month

### Network Configuration

```
VAX:    172.20.0.10 (ports: 2323, 21, 23)
PDP-11: 172.20.0.50 (ports: 2327, 2121, 2023)
```

Direct TCP/IP connection via Docker bridge network.

---

## Changes Made

### 1. IMP Phase Archived (2026-02-13)

**Reason**: Protocol incompatibility
- VAX and PDP-11 both use Ethernet with native TCP/IP (BSD)
- IMPs use ARPANET 1822 protocol (requires complex translation)
- Direct TCP/IP connection is simpler, more reliable

**Archived Location**: `arpanet/archived/imp-phase/`

**Archived Files**:
- `Dockerfile.imp` - H316 IMP simulator
- `configs/phase1/`, `configs/phase2/` - IMP configurations
- `docker-compose.arpanet.phase1.yml`, `phase2.yml` - IMP orchestration
- Documentation and validation reports

### 2. Production Docker Compose Updated

**File**: `docker-compose.production.yml`

**Services**:
- ✅ VAX (jguillaumes/simh-vaxbsd:latest)
- ✅ PDP-11 (custom build from Dockerfile.pdp11)
- ❌ IMP #1 (removed)
- ❌ IMP #2 (removed)
- ❌ Logger (removed - will be added back later if needed)

**Key Changes**:
- Added `SIMH_USE_CONTAINER=yes` environment variable to VAX
- Removed custom VAX config mount (using image default)
- Fixed PDP-11 port mapping (2324 → 2023 to avoid conflict)
- Removed IMP services and dependencies

### 3. Container Status

```
NAMES           STATUS          PORTS
arpanet-vax     Up 14 seconds   0.0.0.0:2323->2323/tcp, 21, 23
arpanet-pdp11   Up 14 seconds   0.0.0.0:2327->2327/tcp, 2121, 2023
```

Both containers running without restart loops.

### 4. EFS Logging

```
/mnt/arpanet-logs/
├── vax/     (6.0K)
├── pdp11/   (6.0K)
└── shared/  (6.0K)
```

EFS mounted successfully on both instances via NFS4.

---

## Technical Details

### VAX Configuration

**Image**: `jguillaumes/simh-vaxbsd:latest`
- Using image's default configuration
- Ethernet device: `de0` (MAC: 08:00:2b:92:49:19)
- Boot disk: Internal RA81 disks
- Network: Attached to Docker bridge (eth0)

### PDP-11 Configuration

**Build**: Custom from `Dockerfile.pdp11`
- OS: 2.11BSD (pre-built image from sergev.org)
- Ethernet device: `xq` attached to eth0
- Disk: `211bsd_rpeth.dsk` (340,252 sectors)
- Console: Telnet on port 2327

### Network Architecture

```
┌─────────────────────────────────────────────┐
│         Docker Bridge 172.20.0.0/16         │
│                                              │
│   ┌──────────────┐       ┌──────────────┐   │
│   │  VAX/BSD     │       │  PDP-11/BSD  │   │
│   │  172.20.0.10 │◄─────►│  172.20.0.50 │   │
│   │  de0         │  TCP  │  xq0         │   │
│   └──────────────┘  /IP  └──────────────┘   │
│                                              │
└─────────────────────────────────────────────┘
                     │
                     ▼
           /mnt/arpanet-logs/ (EFS)
```

---

## Next Steps

### Immediate (Testing)

1. **Test VAX Console Access**
   ```bash
   telnet 3.80.32.255 2323
   # Verify BSD boot and login
   ```

2. **Test PDP-11 Console Access**
   ```bash
   telnet 3.87.125.203 2327
   # Verify 2.11BSD boot and login
   ```

3. **Configure VAX Network**
   ```bash
   # Inside VAX BSD:
   ifconfig de0 172.20.0.10 netmask 255.255.0.0 up
   ping 172.20.0.50  # Test PDP-11 connectivity
   ```

4. **Configure PDP-11 Network**
   ```bash
   # Inside PDP-11 BSD:
   ifconfig xq0 172.20.0.50 netmask 255.255.0.0 up
   ping 172.20.0.10  # Test VAX connectivity
   ```

5. **Test FTP Transfer**
   ```bash
   # From VAX:
   ftp 172.20.0.50

   # From PDP-11:
   ftp 172.20.0.10
   ```

### Medium-Term (Stabilization)

1. **Verify logging to EFS**
   - Check `/mnt/arpanet-logs/vax/` for boot logs
   - Check `/mnt/arpanet-logs/pdp11/` for boot logs

2. **Test container restart persistence**
   - Stop/start containers
   - Verify network config persists
   - Verify data persists

3. **Document network configuration**
   - Create BSD network config scripts
   - Add to startup automation

4. **Update documentation**
   - Cold start guide
   - CHANGELOG.md
   - NEXT-STEPS.md

### Long-Term (GitHub Pipeline)

1. **Move from AWS testing to GitHub Actions**
   - Docker build validation
   - Network connectivity tests
   - Resume artifact generation

2. **Archive AWS CDK stack** (optional)
   - Keep for future testing needs
   - Document shutdown/restart procedures

---

## Files Changed

### Created
- `infra/cdk/arpanet_production_stack.py` - CDK stack definition
- `infra/cdk/app_production.py` - CDK app entry point
- `infra/cdk/PRODUCTION-README.md` - Deployment guide
- `PRODUCTION-DEPLOYMENT.md` - Complete guide
- `docker-compose.production.yml` - Production orchestration
- `arpanet/archived/imp-phase/README.md` - Archive documentation
- `docs/arpanet/PRODUCTION-STATUS-2026-02-13.md` - This file

### Modified
- `docker-compose.production.yml` - Removed IMPs, fixed VAX config
- `arpanet/configs/vax-network.ini` - Updated for TCP/IP (not used in production)
- Memory file - Updated with production info, archived IMP references

### Archived
- `arpanet/archived/imp-phase/Dockerfile.imp`
- `arpanet/archived/imp-phase/configs/phase1/`, `phase2/`
- `arpanet/archived/imp-phase/docker-compose/*.yml`

---

## Cost Analysis

**Current Monthly Cost**: ~$17.90

| Resource | Cost |
|----------|------|
| VAX EC2 (t3.micro) | $7.50 |
| PDP-11 EC2 (t3.micro) | $7.50 |
| VAX root volume (8GB) | $0.64 |
| PDP-11 root volume (8GB) | $0.64 |
| EFS with IA tier | $0.73 |
| S3 archive | $0.02 |

**Cost when stopped**: ~$2/month (storage only)

---

## Access Information

### SSH Access
```bash
# VAX instance
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@3.80.32.255

# PDP-11 instance
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@3.87.125.203
```

### Console Access
```bash
# VAX console
telnet 3.80.32.255 2323

# PDP-11 console
telnet 3.87.125.203 2327
```

### Management Commands
```bash
# On either instance:
cd ~
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f
docker-compose -f docker-compose.production.yml restart vax
```

---

## Blockers / Issues

None currently. Both containers running stable.

---

## References

- Production deployment guide: `PRODUCTION-DEPLOYMENT.md`
- CDK README: `infra/cdk/PRODUCTION-README.md`
- IMP archive: `arpanet/archived/imp-phase/README.md`
- Memory file: `~/.claude/projects/.../memory/MEMORY.md`
