# ARPANET Next Steps: KL10 + Serial + FTP

**Date**: 2026-02-11
**Current Phase**: Phase 1 - Fix PDP-10 Boot (KL10 Switch)
**Goal**: VAX → PDP-10 file transfer via serial tunnel

---

## Quick Status

**Current Blocker**: PDP-10 cannot boot (KS10 emulator incompatible)
**Solution**: Switch to KL10 emulator (community-proven for TOPS-20)
**Master Plan**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`

**Three Phases**:
1. ✋ **Phase 1**: Fix PDP-10 boot (KL10 emulator) - **IN PROGRESS**
2. ⏸️ **Phase 2**: Serial tunnel VAX ↔ PDP-10
3. ⏸️ **Phase 3**: FTP file transfer

---

## Phase 1: Fix PDP-10 Boot (KL10 Switch)

### Step 1.1: Create KL10 Dockerfile (30 min)

**File**: `arpanet/Dockerfile.pdp10-kl10`

```dockerfile
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    ca-certificates \
    libedit-dev \
    libpng-dev \
    telnet \
    socat \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Build SIMH with KL10 (not KS10)
WORKDIR /tmp
RUN git clone https://github.com/simh/simh.git && \
    cd simh && \
    make pdp10

# Install SIMH
RUN mkdir -p /usr/local/bin && \
    cp /tmp/simh/BIN/pdp10 /usr/local/bin/ && \
    chmod +x /usr/local/bin/pdp10

# Download TOPS-20 V4.1 installation tape
RUN mkdir -p /machines/pdp10 && \
    cd /machines/pdp10 && \
    wget -q http://pdp-10.trailing-edge.com/tapes/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2 && \
    bunzip2 bb-d867e-bm_tops20_v41_2020_instl.tap.bz2

# Create data directory for disk
RUN mkdir -p /machines/data

# Copy configs
COPY arpanet/configs/kl10-install.ini /machines/pdp10/install.ini
COPY arpanet/configs/kl10-runtime.ini /machines/pdp10/runtime.ini

WORKDIR /machines/pdp10

# Start with installation config
CMD ["pdp10", "install.ini"]
```

**Action**: `vim arpanet/Dockerfile.pdp10-kl10` and paste above

---

### Step 1.2: Create KL10 Installation Config (15 min)

**File**: `arpanet/configs/kl10-install.ini`

```ini
; KL10 TOPS-20 V4.1 Installation
; Based on working Gunkies recipe

; Enable debug output
set debug stdout

; CPU configuration for TOPS-20
set cpu tops-20

; Set WRU character (Control-F)
d wru 006

; Disable unused devices
set dz disabled
set lp20 disabled

; Tape drive for installation
set tu enable
set tu locked
attach tu /machines/pdp10/tops20_v41.tap

; Disk drive (RP06, 176MB)
set rp enable
set rp rp06
attach rp /machines/data/tops20.dsk

; Console configuration
set console notelnet
set console wru=006

; Boot from tape (interactive installation)
; User will complete installation manually
echo ===================================================
echo KL10 TOPS-20 V4.1 Installation
echo ===================================================
echo At MTBOOT> prompt, type:
echo   /L
echo   /G143
echo ===================================================

boot tu
```

**Action**: `vim arpanet/configs/kl10-install.ini` and paste above

---

### Step 1.3: Create KL10 Runtime Config (15 min)

**File**: `arpanet/configs/kl10-runtime.ini`

```ini
; KL10 TOPS-20 V4.1 Runtime Configuration
; Used after installation is complete

; Enable debug output
set debug stdout

; CPU configuration for TOPS-20
set cpu tops-20

; Set WRU character
d wru 006

; Disable unused devices
set dz disabled
set lp20 disabled

; Disk drive (RP06, 176MB)
set rp enable
set rp rp06
attach rp /machines/data/tops20.dsk

; Console configuration
set console notelnet
set console wru=006

; Telnet console on port 2326
set console telnet=2326

; Serial port for VAX connection (TTY0)
set dz lines=1
set dz 0 speed=9600
attach dz 0 localhost:9001

; Boot from disk
boot rp
```

**Action**: `vim arpanet/configs/kl10-runtime.ini` and paste above

---

### Step 1.4: Update Docker Compose (15 min)

**File**: `docker-compose.vax-pdp10-serial.yml`

**Replace pdp10 service** with:

```yaml
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
      - "9001:9001"  # Serial tunnel
    volumes:
      - pdp10-data:/machines/data
    stdin_open: true
    tty: true
```

**Action**: `vim docker-compose.vax-pdp10-serial.yml` and update

---

### Step 1.5: Deploy to AWS and Test (3-4 hours)

#### Deploy Infrastructure

```bash
# From local machine (Raspberry Pi)
cd ~/brfid.github.io/test_infra/cdk
source ../../.venv/bin/activate
cdk deploy

# Note the IP address from output
```

#### SSH and Build

```bash
# Connect to AWS instance
ssh ubuntu@<AWS_IP>

# Navigate to repo
cd brfid.github.io

# Pull latest changes (after committing locally)
git pull origin main

# Build KL10 container
docker-compose -f docker-compose.vax-pdp10-serial.yml build pdp10

# Expected: Build succeeds, SIMH compiles
```

#### Test PDP-10 Boot

```bash
# Start PDP-10 container
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d pdp10

# Attach to console (interactive)
docker attach pdp10-kl10

# Expected output:
#   BOOT V11.0(315)
#   MTBOOT>

# If you see MTBOOT> prompt, boot is successful! ✅
```

#### Install TOPS-20 (Interactive)

**At MTBOOT> prompt**:

```
MTBOOT> /L
MTBOOT> /G143

! You'll see prompts for logical name and device
LOGICAL-NAME: DSK
DEVICE-NAME: RPA0

! Format the disk
*FORMAT/UNIT:0 RPA0:

! Restore files from tape
*DUMPER
DUMPER> TAPE TU0:
DUMPER> RESTORE <*>*.*.* (TO) DSK:*.*.*
DUMPER> EXIT

! Boot from disk
*^E
MTBOOT> /G144

! You should see TOPS-20 prompt
@
```

**Success Criteria**:
- ✅ MTBOOT> prompt appears
- ✅ Disk formats without errors
- ✅ Files restore from tape
- ✅ System boots to `@` prompt

**Evidence**: Save session transcript to `build/arpanet/validation/kl10-phase1-install.log`

---

### Step 1.6: Verify TOPS-20 Functionality (30 min)

**At `@` prompt**:

```
@ENABLE
$SHOW SYSTEM

! Create test directory and file
@CREATE-DIRECTORY <OPERATOR>
$CREATE <OPERATOR>TEST.TXT
This is a test file on TOPS-20
^Z

@DIRECTORY <OPERATOR>

@TYPE <OPERATOR>TEST.TXT
```

**Success Criteria**:
- ✅ `SHOW SYSTEM` works
- ✅ Can create directories
- ✅ Can create and read files
- ✅ System stable (no crashes)

**Phase 1 Complete**: ✅ PDP-10 boots, TOPS-20 operational

---

## Phase 2: Serial Tunnel (After Phase 1)

### Step 2.1: Start Both Containers

```bash
# On AWS instance
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d

# Verify both running
docker-compose ps
# Expected: vax (Up), pdp10 (Up)
```

### Step 2.2: Create Serial Tunnel Script

```bash
# On AWS instance
cat > ~/serial-tunnel.sh << 'EOF'
#!/bin/bash

echo "Starting serial tunnel..."

# Kill any existing socat processes
pkill -f "socat.*9000"
pkill -f "socat.*9001"

# VAX serial → TCP 9000
socat TCP-LISTEN:9000,bind=0.0.0.0,fork,reuseaddr TCP:172.20.0.10:2323 &
PID1=$!

# PDP-10 serial → TCP 9001
socat TCP-LISTEN:9001,bind=0.0.0.0,fork,reuseaddr TCP:172.20.0.40:2326 &
PID2=$!

# Cross-connect
socat TCP:127.0.0.1:9000 TCP:127.0.0.1:9001 &
PID3=$!

echo "Serial tunnel active:"
echo "  VAX console: telnet localhost 9000 (PID: $PID1)"
echo "  PDP-10 console: telnet localhost 9001 (PID: $PID2)"
echo "  Tunnel bridge: 9000 ↔ 9001 (PID: $PID3)"
echo ""
echo "To stop: kill $PID1 $PID2 $PID3"
EOF

chmod +x ~/serial-tunnel.sh
~/serial-tunnel.sh
```

### Step 2.3: Test Serial Connectivity

```bash
# Test VAX console
telnet localhost 9000
# Should see VAX login prompt

# Test PDP-10 console (different terminal)
telnet localhost 9001
# Should see @ prompt

# Type on one, verify appears on other
```

**Success Criteria**:
- ✅ Both consoles accessible
- ✅ Characters echo between systems
- ✅ Tunnel stable for 5+ minutes

**Phase 2 Complete**: ✅ Serial tunnel working

---

## Phase 3: File Transfer (After Phase 2)

### Step 3.1: Verify Network Connectivity

```bash
# From VAX console
ping -c 3 172.20.0.40

# Expected: 3 packets transmitted, 3 received
```

### Step 3.2: Enable FTP on PDP-10

**On PDP-10 console**:

```
@ENABLE
$SET SERVER FTP ENABLED
$START FTP
$^E

@INFORMATION FTP-SERVER
```

**Test FTP listening**:

```bash
# From AWS host
telnet 172.20.0.40 21
# Expected: 220 ... FTP server ready
```

### Step 3.3: Transfer File

**On VAX console**:

```
$ cat > /tmp/vax-test.txt
This file was created on VAX BSD 4.3
and transferred to PDP-10 TOPS-20
via FTP over serial tunnel.
^D

$ ftp 172.20.0.40
Name: OPERATOR
Password: [password]
ftp> binary
ftp> put /tmp/vax-test.txt vax-test.txt
ftp> quit
```

**Verify on PDP-10**:

```
@TYPE <OPERATOR>VAX-TEST.TXT
```

**Success Criteria**:
- ✅ FTP connection succeeds
- ✅ File transfers without errors
- ✅ File contents correct on PDP-10
- ✅ Checksums match

**Phase 3 Complete**: ✅ **File transfer working!**

---

## Quick Reference Commands

### AWS Deployment

```bash
# Deploy
cd test_infra/cdk && source ../../.venv/bin/activate && cdk deploy

# Connect
ssh ubuntu@<AWS_IP>

# Destroy (when done)
cd test_infra/cdk && cdk destroy --force
```

### Docker Operations

```bash
# Build
docker-compose -f docker-compose.vax-pdp10-serial.yml build

# Start
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d

# Logs
docker logs pdp10-kl10
docker logs vax-host

# Attach
docker attach pdp10-kl10

# Stop
docker-compose -f docker-compose.vax-pdp10-serial.yml down
```

### Testing

```bash
# Console access
telnet localhost 2326  # PDP-10 direct
telnet localhost 2323  # VAX direct
telnet localhost 9000  # VAX via tunnel
telnet localhost 9001  # PDP-10 via tunnel

# Network test
docker exec vax-host ping -c 3 172.20.0.40

# FTP test
docker exec vax-host ftp 172.20.0.40
```

---

## Troubleshooting

### PDP-10 Won't Boot

**Check**:
1. `docker logs pdp10-kl10` for errors
2. SIMH built correctly: `docker exec pdp10-kl10 pdp10 --version`
3. Tape file exists: `docker exec pdp10-kl10 ls -lh /machines/pdp10/tops20_v41.tap`
4. Config syntax: Review `kl10-install.ini`

**Try**:
- Rebuild with `--no-cache`
- Use pre-built TOPS-20 disk image
- Check SIMH logs for specific error

### Serial Tunnel Not Working

**Check**:
1. `ps aux | grep socat` - Are processes running?
2. `netstat -tuln | grep 900` - Are ports listening?
3. Container network: `docker network inspect serial-net`

**Try**:
- Kill and restart tunnel script
- Check firewall rules
- Verify container IPs match config

### FTP Connection Fails

**Check**:
1. FTP server running: `@INFO FTP-SERVER` on PDP-10
2. Network connectivity: `ping 172.20.0.40` from VAX
3. Port 21 accessible: `telnet 172.20.0.40 21`

**Try**:
- Restart FTP server on PDP-10
- Check TOPS-20 user accounts
- Try Python ftplib as alternative

---

## Current Action Items

**Next immediate steps**:

1. [ ] Create `arpanet/Dockerfile.pdp10-kl10`
2. [ ] Create `arpanet/configs/kl10-install.ini`
3. [ ] Create `arpanet/configs/kl10-runtime.ini`
4. [ ] Update `docker-compose.vax-pdp10-serial.yml`
5. [ ] Commit changes to git
6. [ ] Deploy to AWS
7. [ ] Test PDP-10 boot
8. [ ] Install TOPS-20
9. [ ] Document Phase 1 results

**Ready to begin**: Start with Step 1.1

---

**Status**: Phase 1 ready to start
**Blocker**: None (plan complete)
**Next Command**: `vim arpanet/Dockerfile.pdp10-kl10`
**Estimated Time**: 6-10 hours total
**AWS Cost**: ~$0.40-$0.80
