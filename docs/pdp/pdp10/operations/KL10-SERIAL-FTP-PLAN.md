# KL10 + Serial + FTP Master Plan

**Date**: 2026-02-11
**Goal**: VAX → PDP-10 file transfer via serial tunnel
**Approach**: Fix PDP-10 boot (KL10), connect via serial, transfer via FTP
**Testing**: All testing on AWS (local Raspberry Pi incompatible)

---

## Executive Summary

Three-phase plan to achieve VAX→PDP-10 file transfer:

**Phase 1**: Fix PDP-10 Boot (Switch to KL10 emulator)
**Phase 2**: Establish Serial Connection (VAX ↔ PDP-10)
**Phase 3**: Transfer File via FTP (or alternative if needed)

**Estimated Total Time**: 6-10 hours on AWS
**Cost**: ~$0.40-$0.80 (10 hours × $0.04/hr for t3.medium)

---

## Background: Why This Plan

### Current Blockers

1. **KS10 Emulator Cannot Boot**
   - ITS: Fails with "Internal error, PC: 000100"
   - TOPS-20: Fails with "Unknown stop code 7, PC: 000100"
   - Both confirmed incompatible with SIMH KS10

2. **IMP Chain Archived**
   - HI1 framing mismatch (KS10 vs H316 protocols)
   - Complex multi-hop routing unnecessary for file transfer

3. **Chaosnet Path Archived**
   - ITS build timeout (30-60+ minutes, incomplete)
   - Requires working PDP-10 endpoint first

### Solution: Direct Serial + KL10

**Why Serial Tunnel**:
- Simplest VAX↔PDP connection (no IMP complexity)
- TCP-based serial port forwarding (socat)
- Direct host-to-host communication
- Proven technology, minimal configuration

**Why KL10 Emulator**:
- Community-proven to boot TOPS-20 (Gunkies recipe)
- All working TOPS-20 setups use KL10 or KLH10
- Pre-built images available (Panda distribution)
- Better TOPS-20 support than KS10

---

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  VAX/4.3BSD     │  TCP    │  Serial-TCP     │  TCP    │  PDP-10/TOPS-20 │
│  SIMH VAX       │◄───────►│  Tunnel (socat) │◄───────►│  SIMH KL10      │
│  172.20.0.10    │  :9000  │                 │  :9001  │  172.20.0.40    │
│  Console: 2323  │         │                 │         │  Console: 2326  │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                                                        │
        │                    Docker Bridge                       │
        │                    172.20.0.0/16                       │
        │                                                        │
        └────────────────────────────────────────────────────────┘
```

**Key Changes from Previous Attempts**:
- ❌ No IMPs (archived due to HI1 framing mismatch)
- ❌ No Chaosnet (archived due to ITS build blocker)
- ✅ Direct VAX-PDP connection via serial
- ✅ KL10 emulator (not KS10)
- ✅ TOPS-20 (proven to work on KL10)

---

## Phase 1: Fix PDP-10 Boot (KL10 Switch)

**Goal**: Get PDP-10 container booting successfully with TOPS-20

**Estimated Time**: 3-5 hours

### 1.1: Update Dockerfile (30 min)

**File**: `arpanet/Dockerfile.pdp10-kl10` (new)

**Changes**:
```dockerfile
# Build SIMH with KL10 target (not KS10)
RUN cd simh && \
    make pdp10  # This builds KL10 by default

# Use working TOPS-20 installation tape
ADD http://pdp-10.trailing-edge.com/tapes/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2 /tmp/
RUN bunzip2 /tmp/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2 && \
    mv /tmp/bb-d867e-bm_tops20_v41_2020_instl.tap /machines/pdp10/

# Create KL10-compatible init file
COPY arpanet/configs/kl10-install.ini /machines/pdp10/install.ini
```

### 1.2: Create KL10 SIMH Config (30 min)

**File**: `arpanet/configs/kl10-install.ini`

**Based on Gunkies recipe** (proven working):
```ini
; KL10 TOPS-20 V4.1 Installation
set cpu tops-20
d wru 006

; Tape drive
set tu enable
att tu /machines/pdp10/tops20_v41.tap

; Disk drive (RP06, 176MB)
set rp rp06
att rp /machines/data/tops20.dsk

; Console
set console notelnet

; Boot from tape
boot tu
```

### 1.3: Update Docker Compose (15 min)

**File**: `docker-compose.vax-pdp10-serial.yml`

```yaml
services:
  vax:
    # ... existing VAX config

  pdp10:
    build:
      context: .
      dockerfile: arpanet/Dockerfile.pdp10-kl10
    container_name: pdp10-kl10
    hostname: pdp10
    networks:
      serial-net:
        ipv4_address: 172.20.0.40
    ports:
      - "2326:2326"  # Console
    volumes:
      - pdp10-data:/machines/data
    stdin_open: true
    tty: true

networks:
  serial-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  vax-data:
  pdp10-data:
```

### 1.4: Test PDP-10 Boot on AWS (1-2 hours)

**Deploy to AWS**:
```bash
# Local machine
cd test_infra/cdk
source ../../.venv/bin/activate
cdk deploy

# SSH to instance
ssh ubuntu@<AWS_IP>
cd brfid.github.io

# Build new KL10 container
docker-compose -f docker-compose.vax-pdp10-serial.yml build pdp10

# Start PDP-10 only (test boot)
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d pdp10

# Watch boot process
docker logs -f pdp10-kl10
```

**Success Criteria**:
```
Expected output:
  BOOT V11.0(315)
  MTBOOT>
```

**If success**: Proceed to TOPS-20 installation
**If failure**: Debug using `docker attach pdp10-kl10` for interactive console

### 1.5: Install TOPS-20 (1-2 hours)

**Interactive installation** (from MTBOOT> prompt):

```
MTBOOT> /L
MTBOOT> /G143

!Define system disk
LOGICAL-NAME: DSK
DEVICE-NAME: RPA0

!Initialize disk
*FORMAT/UNIT:0 RPA0:

!Restore from tape
*DUMPER
DUMPER> TAPE TU0:
DUMPER> RESTORE <*>*.*.* (TO) DSK:*.*.*
DUMPER> EXIT

!Boot from disk
MTBOOT> /G144
@ENABLE
$DEFINE SYSTEM-STARTUP-FILE DSK:SYSTEM.CMD
$^E
```

**Success Criteria**:
- Disk formatted without errors
- Files restored from tape
- System boots to `@` prompt
- `SHOW SYSTEM` works

### 1.6: Configure TOPS-20 for Serial (30 min)

**Enable serial port** (TTY for serial connection):

```
@ENABLE
$SET TTY 0: SPEED 9600
$SET TTY 0: WIDTH 80
$^E
@
```

**Test serial console**:
```bash
# From AWS host
telnet localhost 2326
# Should see @ prompt
```

**Phase 1 Complete**: ✅ PDP-10 boots, TOPS-20 operational

---

## Phase 2: Serial Connection (VAX ↔ PDP-10)

**Goal**: Establish working serial tunnel between VAX and PDP-10

**Estimated Time**: 1-2 hours

### 2.1: Start Both Containers (15 min)

```bash
# On AWS instance
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d

# Verify both running
docker-compose ps
# Should show: vax (Up), pdp10 (Up)
```

### 2.2: Set Up Serial Tunnel (15 min)

**Using socat** (TCP port forwarding):

```bash
# Create tunnel script
cat > /tmp/serial-tunnel.sh << 'EOF'
#!/bin/bash
# VAX serial port (DZ11) → TCP 9000
socat TCP-LISTEN:9000,bind=127.0.0.1,fork TCP:172.20.0.10:2323 &

# PDP-10 serial port (TTY) → TCP 9001
socat TCP-LISTEN:9001,bind=127.0.0.1,fork TCP:172.20.0.40:2326 &

# Cross-connect: VAX ↔ PDP-10
socat TCP:127.0.0.1:9000 TCP:127.0.0.1:9001 &

echo "Serial tunnel active:"
echo "  VAX console: telnet localhost 9000"
echo "  PDP-10 console: telnet localhost 9001"
echo "  Tunnel: 9000 ↔ 9001"
EOF

chmod +x /tmp/serial-tunnel.sh
/tmp/serial-tunnel.sh
```

### 2.3: Test Serial Connectivity (30 min)

**Test 1: Console Access**
```bash
# From VAX to PDP-10
telnet localhost 9000
# Type characters, should appear on PDP-10

# From PDP-10 to VAX
telnet localhost 9001
# Type characters, should appear on VAX
```

**Test 2: Serial Echo**
```bash
# On VAX console
$ echo "Hello from VAX" > /dev/tty01

# Should appear on PDP-10 console
```

**Success Criteria**:
- ✅ Can access VAX via port 9000
- ✅ Can access PDP-10 via port 9001
- ✅ Characters typed on one side appear on other
- ✅ Serial tunnel stable (no disconnects)

**Phase 2 Complete**: ✅ VAX and PDP-10 connected via serial

---

## Phase 3: File Transfer (FTP)

**Goal**: Transfer file from VAX to PDP-10

**Estimated Time**: 2-3 hours

### 3.1: Verify Network Connectivity (15 min)

**Both systems on same Docker network**:

```bash
# From VAX
docker exec vax-host ping -c 3 172.20.0.40

# Expected: 3 packets transmitted, 3 received
```

### 3.2: Enable FTP on PDP-10 (30 min)

**On PDP-10 TOPS-20 console**:

```
@ENABLE
$SET SERVER FTP ENABLED
$START FTP
$^E

@CREATE-DIRECTORY <OPERATOR>
@CREATE <OPERATOR>USER-1.TXT
This is a test file on PDP-10
^Z

@DIRECTORY <OPERATOR>
```

**Test FTP server listening**:
```bash
# From AWS host
telnet 172.20.0.40 21
# Should see: 220 ... FTP server ready
```

### 3.3: Test VAX → PDP-10 FTP (1 hour)

**Option A: Using VAX FTP client** (historically authentic)

```bash
# On VAX console
$ cat > /tmp/vax-test.txt
This file was created on VAX BSD 4.3
and transferred to PDP-10 via FTP
^D

$ ftp 172.20.0.40
Name: OPERATOR
Password: [password]
ftp> binary
ftp> put /tmp/vax-test.txt <OPERATOR>vax-test.txt
ftp> quit

# Verify on PDP-10
@TYPE <OPERATOR>VAX-TEST.TXT
```

**Option B: Using Python ftplib** (if VAX client fails)

```python
# On AWS host
from ftplib import FTP

# Connect to PDP-10
ftp = FTP('172.20.0.40')
ftp.login('OPERATOR', 'password')

# Get file from VAX
with open('/tmp/from-vax.txt', 'rb') as f:
    ftp.storbinary('STOR vax-test.txt', f)

ftp.quit()
print("Transfer complete!")
```

### 3.4: Verify File Integrity (30 min)

```bash
# Compare checksums
md5sum /tmp/vax-test.txt          # On VAX
md5sum <OPERATOR>vax-test.txt     # On PDP-10

# Should match
```

**Success Criteria**:
- ✅ FTP connection established
- ✅ File transferred VAX → PDP-10
- ✅ File contents identical (checksum match)
- ✅ No corruption or truncation

**Phase 3 Complete**: ✅ File transfer working!

---

## Testing Strategy

### Incremental Testing (After Each Phase)

**Phase 1 Tests**:
1. PDP-10 container starts without restart loop
2. TOPS-20 boots to `@` prompt
3. `SHOW SYSTEM` command works
4. Telnet console accessible on port 2326

**Phase 2 Tests**:
1. Both containers running simultaneously
2. Serial tunnel processes active
3. Console access via tunnel ports
4. Character echo VAX ↔ PDP-10

**Phase 3 Tests**:
1. Network ping VAX → PDP-10
2. FTP server listening on port 21
3. FTP login successful
4. File transfer completes
5. File integrity verified

### Rollback Points

**If Phase 1 fails** (KL10 boot):
- Check KL10 build logs
- Verify tape file integrity
- Try pre-built TOPS-20 disk image
- Fallback: Try TOPS-10 instead

**If Phase 2 fails** (Serial tunnel):
- Test each socat command individually
- Verify console ports accessible
- Check Docker network connectivity
- Fallback: Use direct network FTP (skip serial)

**If Phase 3 fails** (FTP):
- Test with simpler FTP client
- Try TFTP instead of FTP
- Use rcp or scp if available
- Fallback: Manual file copy via console

### Evidence Collection

**For each phase, capture**:
1. Docker logs: `docker logs pdp10-kl10 > phase1-boot.log`
2. Console transcript: Script session to file
3. Network tests: `ping`, `telnet` output
4. File checksums: md5sum before/after
5. Success screenshots: Console prompts, file listings

**Commit evidence to**:
- `build/arpanet/validation/kl10-phase1-*.log`
- `build/arpanet/validation/kl10-phase2-*.log`
- `build/arpanet/validation/kl10-phase3-*.log`

---

## File Changes Required

### New Files

| File | Purpose |
|------|---------|
| `arpanet/Dockerfile.pdp10-kl10` | KL10 emulator build |
| `arpanet/configs/kl10-install.ini` | KL10 SIMH installation config |
| `arpanet/configs/kl10-runtime.ini` | KL10 SIMH runtime config |
| `arpanet/scripts/kl10-install.exp` | Automated TOPS-20 installation |
| `docs/arpanet/KL10-SERIAL-FTP-PLAN.md` | This document |
| `docs/arpanet/validation/KL10-PHASE1-RESULTS.md` | Phase 1 test results |
| `docs/arpanet/validation/KL10-PHASE2-RESULTS.md` | Phase 2 test results |
| `docs/arpanet/validation/KL10-PHASE3-RESULTS.md` | Phase 3 test results |

### Modified Files

| File | Changes |
|------|---------|
| `docker-compose.vax-pdp10-serial.yml` | Update for KL10 container |
| `CHANGELOG.md` | Update current path and next steps |
| `docs/arpanet/progress/NEXT-STEPS.md` | Replace with KL10 plan |
| `docs/arpanet/SERIAL-TUNNEL.md` | Update for KL10 requirement |
| `docs/COLD-START.md` | Update quick start instructions |

### Archived Files

| File | Reason | Destination |
|------|--------|-------------|
| `docs/arpanet/handoffs/LLM-RUNTIME-BOOT-LOOP-2026-02-09.md` | KS10 blocker, superseded by KL10 | `docs/arpanet/archive/ks10/` |
| `docs/arpanet/archive/tops20/TOPS20-TAPE-BOOT-FAILURE.md` | KS10 blocker, superseded by KL10 | `docs/arpanet/archive/ks10/` |
| `arpanet/Dockerfile.pdp10-its` | ITS build blocker, using TOPS-20 | `arpanet/archived/` |
| `arpanet/Dockerfile.pdp10` | KS10 version, replaced by KL10 | `arpanet/archived/` |

---

## AWS Deployment Workflow

### 1. Deploy Infrastructure

```bash
# Local (Raspberry Pi)
cd ~/brfid.github.io/test_infra/cdk
source ../../.venv/bin/activate
cdk deploy

# Note the IP address
# Output: Instance IP: 34.xxx.xxx.xxx
```

### 2. Connect and Setup

```bash
# SSH to instance
ssh ubuntu@34.xxx.xxx.xxx
cd brfid.github.io

# Pull latest code
git pull origin main

# Build containers
docker-compose -f docker-compose.vax-pdp10-serial.yml build
```

### 3. Execute Phases

**Phase 1**:
```bash
# Start PDP-10 only
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d pdp10

# Watch boot
docker logs -f pdp10-kl10

# If successful, install TOPS-20 (interactive)
docker attach pdp10-kl10
```

**Phase 2**:
```bash
# Start both
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d

# Setup tunnel
/tmp/serial-tunnel.sh

# Test connectivity
telnet localhost 9000  # VAX
telnet localhost 9001  # PDP-10
```

**Phase 3**:
```bash
# Test FTP from VAX console
docker exec -it vax-host telnet localhost 2323
# Login and run FTP commands
```

### 4. Collect Evidence and Cleanup

```bash
# Collect logs
docker logs pdp10-kl10 > ~/phase1-complete.log
docker logs vax-host > ~/vax-logs.log

# Copy to local (from Pi)
scp ubuntu@34.xxx.xxx.xxx:~/phase*.log ~/brfid.github.io/build/arpanet/validation/

# Destroy AWS resources (if done)
cd test_infra/cdk
cdk destroy --force
```

---

## Success Criteria

### Phase 1: PDP-10 Boot
- [ ] PDP-10 container starts without errors
- [ ] TOPS-20 boots to `@` prompt
- [ ] Console accessible via telnet
- [ ] `SHOW SYSTEM` command works
- [ ] No restart loops

### Phase 2: Serial Connection
- [ ] Both VAX and PDP-10 running
- [ ] Serial tunnel established
- [ ] Can access consoles via tunnel ports
- [ ] Characters echo between systems
- [ ] Connection stable for 5+ minutes

### Phase 3: File Transfer
- [ ] Network ping successful
- [ ] FTP server listening
- [ ] FTP login successful
- [ ] File transfers VAX → PDP-10
- [ ] File integrity verified (checksum match)

**All criteria met** = ✅ **Plan Complete**

---

## Estimated Timeline

| Phase | Task | Time | Cumulative |
|-------|------|------|------------|
| **1** | Update Dockerfile | 30 min | 0.5 hr |
| **1** | Create SIMH config | 30 min | 1 hr |
| **1** | Update docker-compose | 15 min | 1.25 hr |
| **1** | Deploy to AWS | 15 min | 1.5 hr |
| **1** | Test boot | 1 hr | 2.5 hr |
| **1** | Install TOPS-20 | 2 hr | 4.5 hr |
| **1** | Configure serial | 30 min | 5 hr |
| **2** | Start containers | 15 min | 5.25 hr |
| **2** | Setup tunnel | 15 min | 5.5 hr |
| **2** | Test connectivity | 30 min | 6 hr |
| **3** | Enable FTP | 30 min | 6.5 hr |
| **3** | Test transfer | 1 hr | 7.5 hr |
| **3** | Verify integrity | 30 min | 8 hr |
| | **Documentation** | 1 hr | 9 hr |
| | **Buffer** | 1 hr | **10 hr** |

**Total**: 10 hours (worst case)
**Optimistic**: 6-7 hours
**AWS Cost**: ~$0.40 (10 hours × $0.04/hr)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| KL10 build fails | High | Use pre-built KL10 binary |
| TOPS-20 install timeout | Medium | Use pre-installed disk image |
| Serial tunnel unstable | Low | Fallback to direct network FTP |
| FTP auth fails | Low | Create user accounts, try TFTP |
| File corruption | Low | Use binary mode, verify checksums |
| AWS timeout | Medium | Use tmux/screen, save state frequently |

---

## Next Actions

1. **Create KL10 Dockerfile** → `arpanet/Dockerfile.pdp10-kl10`
2. **Create KL10 configs** → `arpanet/configs/kl10-*.ini`
3. **Update docker-compose** → Add KL10 service
4. **Archive KS10 docs** → Move to `docs/arpanet/archive/ks10/`
5. **Update CHANGELOG.md** → Reflect new plan
6. **Deploy to AWS** → Begin Phase 1

---

**Status**: Ready to begin
**Prerequisites**: AWS credentials configured, git repo up to date
**First Command**: `vim arpanet/Dockerfile.pdp10-kl10`
