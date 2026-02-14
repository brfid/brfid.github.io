# Project Status

**Last updated:** 2026-02-14 Evening

---

## 🚨 CURRENT BLOCKER: VAX Build Layer Fix

**Problem**: Scripts execute in container (modern GCC 11.4.0), not inside BSD (vintage K&R C from 1986)

**Impact**: Violates "show not tell" principle - claiming to use vintage tools but actually using modern ones

**Status**: ❌ BLOCKED - Need file sharing method between container and BSD layers

**Research**: `docs/research/VAX-CONTAINER-BSD-FILE-SHARING.md`

**Details**: `docs/integration/ARCHITECTURE-STACK.md` (explains layer confusion)

---

## ✅ JUST SOLVED: PDP-11 /usr Mount Issue (2026-02-14)

**Problem**: PDP-11 appeared to be missing uuencode, uudecode, nroff

**Root Cause**: `/usr` filesystem not mounted at boot (disk image was complete all along!)

**Solution**: Created `arpanet/pdp11-boot.sh` wrapper script that auto-mounts `/usr` after boot

**Verification**: All tools confirmed working:
- ✅ `/usr/bin/uuencode` (6366 bytes, from Nov 1999)
- ✅ `/usr/bin/uudecode` (16716 bytes, from Nov 1999)
- ✅ `/usr/bin/nroff` (44940 bytes, from Nov 1999)

**Testing**: Full workflow tested (encode → decode → render) - all successful

**Doc**: `docs/integration/PDP11-USR-MOUNT-FIX.md`

---

## Current Architecture

### Layer Stack (Critical Understanding)

```
AWS EC2 (Ubuntu 22.04)
  └─ Docker Container (Debian/Ubuntu base)
      └─ SIMH Emulator (Linux binary)
          └─ Emulated Hardware (VAX/PDP-11)
              └─ BSD Unix (4.3BSD / 2.11BSD) ← VINTAGE TOOLS HERE
```

**Problem**: Scripts currently run at **Layer 2** (container with modern tools)

**Goal**: Scripts must run at **Layer 5** (BSD with vintage tools)

**Doc**: `docs/integration/ARCHITECTURE-STACK.md`

---

## Machine Status

### VAX 11/780 (4.3BSD)
- **IP**: 3.80.32.255 (public), 172.20.0.10 (internal)
- **Instance**: t3.micro on AWS
- **Boot**: ✅ Boots to multi-user mode automatically
- **Filesystems**: ✅ All mounted (`/usr`, `/home`, `/usr/src`)
- **Tools**: ✅ `uuencode`, `cc` from Jun 7 1986 - VERIFIED VINTAGE
- **Problem**: ❌ Scripts run in container shell (modern GCC), not BSD (K&R C)
- **Blocker**: No known file sharing method between container and BSD
- **Console**: telnet 3.80.32.255 2323

### PDP-11/73 (2.11BSD)
- **IP**: 3.87.125.203 (public), 172.20.0.50 (internal)
- **Instance**: t3.micro on AWS
- **Boot**: ✅ Boots correctly with auto-mount wrapper
- **Filesystems**: ✅ `/usr` auto-mounted via `pdp11-boot.sh`
- **Tools**: ✅ All utilities present and working
- **Status**: ✅ FULLY OPERATIONAL - Ready for validation workflow
- **Console**: telnet 3.87.125.203 2327

### Infrastructure
- **Shared EFS**: `/mnt/arpanet-logs/` (logs + builds)
- **Network**: Docker bridge 172.20.0.0/16
- **Cost**: ~$17.90/month (~$0.60/day)
- **Management**: `aws-start.sh`, `aws-stop.sh`, `aws-status.sh`

---

## What Works Now

### ✅ PDP-11 Layer
- Boot wrapper auto-mounts `/usr` filesystem
- All vintage tools accessible (uuencode, uudecode, nroff)
- Console automation via screen/telnet proven effective
- Ready to receive files and execute validation

### ✅ Console Transfer
- `scripts/console-transfer.py` - Sends files via terminal I/O
- Works with PDP-11 (will work with VAX once file access solved)
- Rate-limited, reliable transfer

### ✅ Infrastructure
- AWS instances running and accessible
- EFS shared storage working
- Docker networking operational
- Logs merging correctly

---

## What's Broken

### ❌ VAX Build Process
**Problem**: `vax-build-and-encode.sh` runs in container, not BSD

**Current execution** (WRONG):
```bash
ssh ubuntu@$VAX_IP "bash /tmp/vax-build-and-encode.sh"
# Runs in Ubuntu container with GCC 11.4.0
```

**Needed execution** (CORRECT):
```bash
# Send commands to BSD console via telnet
# Execute inside 4.3BSD with K&R C from 1986
```

**Blocker**: Files in container `/tmp/` not visible to BSD

---

## Research Needed

### Primary Question
**How do we share files between container and BSD in `jguillaumes/simh-vaxbsd:latest` image?**

**Research prompt**: `docs/research/VAX-CONTAINER-BSD-FILE-SHARING.md`

**Possible approaches**:
1. FTP (port 21 exposed, is server running in BSD?)
2. SIMH attach (can SIMH mount container directories?)
3. Console I/O (like PDP-11, but for binary files?)
4. Build our own VAX image (like we did for PDP-11)

---

## Next Steps (Priority Order)

### 1. Solve VAX File Sharing (CRITICAL)
- Research `jguillaumes/simh-vaxbsd` image capabilities
- Test FTP from container to BSD
- Or implement console-based file transfer
- Or build custom VAX Docker image

### 2. Test End-to-End Pipeline
Once VAX fixed:
- Generate resume.vax.yaml
- **Compile inside BSD with K&R C**
- **Encode inside BSD with uuencode**
- Transfer to PDP-11 via console
- Decode and render in PDP-11
- Verify output

### 3. Update Workflow
- Modify `.github/workflows/deploy.yml` Stage 1
- Use console-based execution for VAX
- Ensure all commands run inside BSD, not container

---

## Key Documentation

### Must Read for Cold Start
1. **`docs/COLD-START.md`** - Quick start guide (needs update)
2. **`docs/integration/ARCHITECTURE-STACK.md`** - Layer confusion explained
3. **`docs/integration/PDP11-USR-MOUNT-FIX.md`** - PDP-11 solution
4. **`docs/research/VAX-CONTAINER-BSD-FILE-SHARING.md`** - VAX blocker research

### Debugging Session Logs
- `docs/integration/DEBUGGING-SUMMARY-2026-02-14.md` - Full debug session
- `docs/integration/PDP11-DEBUG-FINDINGS.md` - Detailed findings
- `docs/integration/PDP11-DEBUGGING-PLAN.md` - Interactive debugging approach

### Implementation Details
- `arpanet/pdp11-boot.sh` - Auto-mount wrapper (working)
- `arpanet/vax-boot.sh` - Auto-mount wrapper (not needed)
- `scripts/vax-console-build.sh` - Console-based build (blocked)
- `docker-compose.production.yml` - Container configuration

---

## Critical Constraints

- ✅ Use `.venv/` for all Python commands
- ✅ Must ACTUALLY use vintage tools ("show don't tell")
- ✅ No modern GCC claiming to be K&R C
- ✅ Commit at significant milestones only
- ✅ Test thoroughly before claiming success

---

## Environment

**Python**: `.venv/` (must be activated)
**AWS**: Account 972626128180, region us-east-1
**Permissions**: bypassPermissions mode enabled

```bash
# Activate venv
source .venv/bin/activate

# AWS instances
./aws-start.sh  # Start and show IPs
./aws-stop.sh   # Stop (saves money, keeps data)
./aws-status.sh # Check current state

# Connect to machines
ssh -i ~/.ssh/arpanet-temp.pem ubuntu@<ip>
telnet <vax-ip> 2323  # VAX console
telnet <pdp11-ip> 2327  # PDP-11 console
```

---

## Recent Discoveries (2026-02-14)

### PDP-11 Disk Image Is Complete
- Believed to be minimal, actually full 2.11BSD distribution
- All standard utilities present in `/usr/bin/`
- Just needed `/usr` filesystem mounted
- No need for alternative disk images

### VAX Filesystems Already Mounted
- Pre-built image boots correctly
- All filesystems mounted automatically
- Tools exist and are vintage (from 1986!)
- Problem is only script execution layer

### Layer Confusion Is The Core Issue
- Easy to confuse container layer with BSD layer
- `docker exec` runs in container (modern tools)
- `telnet to console` runs in BSD (vintage tools)
- Must execute in BSD to use vintage tools

---

## Success Criteria

### Phase 1: ✅ COMPLETE
- [x] PDP-11 has all required tools
- [x] Auto-mount wrapper working
- [x] Full decode → render workflow tested

### Phase 2: ❌ BLOCKED
- [ ] VAX file sharing method found
- [ ] Scripts execute inside BSD
- [ ] Actual K&R C compilation verified
- [ ] Actual vintage uuencode working

### Phase 3: ⏳ PENDING
- [ ] End-to-end pipeline working
- [ ] All commands in vintage tools
- [ ] Logs accurately reflect tool usage
- [ ] Deployed and operational

---

## Quick Commands

```bash
# Check what's running
./aws-status.sh

# Start instances
./aws-start.sh

# Test VAX console
telnet <vax-ip> 2323
# Login: root
# Check: which uuencode
# Verify: ls -la /usr/bin/uu*

# Test PDP-11 console
telnet <pdp11-ip> 2327
# Login: root
# Check: mount (should show /dev/xp0e on /usr)
# Verify: ls /usr/bin/uu*

# Stop instances (save money)
./aws-stop.sh
```

---

## Files Changed Today (2026-02-14)

**Created**:
- `arpanet/pdp11-boot.sh` - Auto-mount wrapper
- `scripts/vax-console-build.sh` - Console-based build attempt
- `docs/integration/PDP11-USR-MOUNT-FIX.md` - Solution doc
- `docs/integration/ARCHITECTURE-STACK.md` - Layer explanation
- `docs/integration/DEBUGGING-SUMMARY-2026-02-14.md` - Debug session
- `docs/integration/PDP11-DEBUG-FINDINGS.md` - Detailed findings
- `docs/research/PDP11-MISSING-TOOLS-RESEARCH.md` - Research request (solved)
- `docs/research/VAX-CONTAINER-BSD-FILE-SHARING.md` - Research request (open)

**Modified**:
- `arpanet/Dockerfile.pdp11` - Added boot wrapper
- `docker-compose.production.yml` - Updated PDP-11 volume mount + VAX command
- `arpanet/configs/pdp11.ini` - Reviewed (no changes needed)

---

## Git Status

```bash
git log --oneline -10
c14bc33 wip: VAX console build attempt + research prompt for file sharing
11dddff feat: add VAX auto-mount boot wrapper
c12ef1a docs: complete solution for PDP-11 /usr mount fix
c8e0c93 improve: more robust auto-mount with nc and retry logic
299aa75 feat: auto-mount /usr on PDP-11 boot via wrapper script
fba4cf1 docs: research request for PDP-11 missing utilities blocker
878c0eb docs: debugging findings and architecture stack explanation
db411c2 fix: add auto-mount /usr to PDP-11 boot sequence
715bde5 fix: mount full EFS in PDP-11 container for builds access
d1c2d0d fix: ensure build directory exists before uploading logs
```

---

**NEXT SESSION**: Start by reading research prompt in `docs/research/VAX-CONTAINER-BSD-FILE-SHARING.md` and attempting to find solution for VAX file sharing.
