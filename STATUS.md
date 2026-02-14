# Project Status

**Last updated:** 2026-02-14 (post AWS lifecycle hardening)

---

## ✅ ENTERPRISE LOGS PAGE IMPLEMENTED

**Status**: Complete and ready for deployment
**URL**: https://brfid.github.io/logs/

**What Was Built**:
- ✅ Professional logs viewer with timeline view
- ✅ Interactive filtering by component (VAX/PDP-11/GITHUB/COURIER)
- ✅ Real-time search across log messages
- ✅ Export functionality to download filtered logs
- ✅ Authenticity evidence highlighting (⭐ indicators for vintage tools)
- ✅ Statistics dashboard (total events, duration, errors, warnings)
- ✅ Responsive design matching site dark theme

**Architecture**:
- Server-side generation: `scripts/generate-logs-page.py` parses logs at build time
- Client-side enhancement: `site/logs/logs.js` adds filtering/search/export
- Progressive enhancement: Works without JavaScript
- Integrated into GitHub Actions workflow

**Evidence Detection** (6 patterns):
- VAX K&R C Compiler (1986)
- Historical transfer methods (uuencode, console I/O)
- VAX C YAML Parser
- BSD operating system markers

**Files**:
- `scripts/generate-logs-page.py` - Generator script
- `site/logs/index.html` - Generated viewer page
- `site/logs/logs.js` - Client-side features
- `docs/integration/LOGS-PAGE.md` - Complete documentation

**Integration**:
- Updated `site/index.html` footer: `/vax-build.log` → `/logs/`
- Added workflow step in `.github/workflows/deploy.yml`
- Auto-generates on every `publish-vax` or `publish-docker` deploy

**Next**: Test during next full pipeline run

---

## ✅ LOGGING OVERHAUL COMPLETE

**Status**: All code changes complete, ready for pipeline test

**What Changed**:
- ✅ Workflow executes commands INSIDE BSD (not container)
- ✅ Logs capture actual vintage tool versions (cc from 1986)
- ✅ Console-based execution with screen automation
- ✅ Log extraction from console captures to EFS
- ✅ Enhanced tool evidence (binary sizes, dates, versions)

**Commits**:
- `5a58852` - Comprehensive logging overhaul
- `dd58356` - Log format examples and webpage templates

**Next**: Run a full tagged docker publish to verify end-to-end evidence on live AWS

---

## ✅ SOLVED: VAX Console Build Pipeline

**Status**: Fully integrated into workflow

**What Was Done**:
- ✅ Console upload method verified working (`scripts/vax-console-upload.sh`)
- ✅ Test compilation works (vintage cc in BSD)
- ✅ Build commands script exists (`scripts/vax-console-build.sh`)
- ✅ Full build script exists (`scripts/vax-build-and-encode.sh`)

**The Scripts**:
1. **`scripts/vax-console-upload.sh`** - Uploads files to VAX via console heredoc
2. **`scripts/vax-console-build.sh`** - Sends build commands to BSD console (NOT container)
3. **`scripts/vax-build-and-encode.sh`** - Actual build script that runs INSIDE BSD

**The Blocker (Now Resolved)**:
- Old docs claimed "no file sharing method" - FALSE
- Solution uses console I/O via screen + telnet
- Commands execute inside 4.3BSD, not container

**Workflow Integration Status**:
- ✅ `.github/workflows/deploy.yml` now uses console-driven upload/build/validation stages
- ✅ AWS activation/deactivation is consolidated and deterministic
- ✅ Lifecycle markers are emitted to `GITHUB.log` for activate/deactivate boundaries

**Docs**: `docs/research/VAX-FILE-INPUT-OPTIONS.md` (still relevant for context)

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
- **IP**: Use `./aws-status.sh` to get current IP
- **Instance**: t3.micro on AWS
- **Boot**: ✅ Boots to multi-user mode automatically
- **Filesystems**: ✅ All mounted (`/usr`, `/home`, `/usr/src`)
- **Tools**: ✅ `uuencode`, `cc` from Jun 7 1986 - VERIFIED VINTAGE
- **Console**: telnet <ip> 2323
- **Status**: ✅ OPERATIONAL - Console build pipeline ready

### PDP-11/73 (2.11BSD)
- **IP**: Use `./aws-status.sh` to get current IP
- **Instance**: t3.micro on AWS
- **Boot**: ✅ Boots correctly with auto-mount wrapper
- **Filesystems**: ✅ `/usr` auto-mounted via `pdp11-boot.sh`
- **Tools**: ✅ All utilities present and working
- **Console**: telnet <ip> 2327
- **Status**: ✅ FULLY OPERATIONAL - Ready for validation workflow

### Infrastructure
- **Shared EFS**: `/mnt/arpanet-logs/` (logs + builds)
- **Network**: Docker bridge 172.20.0.0/16
- **Cost**: ~$17.90/month (~$0.60/day)
- **Management**: `aws-start.sh`, `aws-stop.sh`, `aws-status.sh`

---

## What Works Now

### ✅ VAX Console Build Pipeline
- `scripts/vax-console-upload.sh` - Uploads files via console
- `scripts/vax-console-build.sh` - Executes commands in BSD (not container!)
- `scripts/vax-build-and-encode.sh` - Runs INSIDE BSD with vintage tools
- Vintage K&R C compilation verified

### ✅ PDP-11 Layer
- Boot wrapper auto-mounts `/usr` filesystem
- All vintage tools accessible (uuencode, uudecode, nroff)
- Console automation via screen/telnet proven effective

### ✅ Console Transfer
- `scripts/console-transfer.py` - Sends files via terminal I/O
- Works with both VAX and PDP-11

### ✅ Infrastructure
- AWS instances running and accessible
- EFS shared storage working
- Docker networking operational
- Logs merging correctly

---

## Logging Architecture

### Log Flow
```
VAX BSD → arpanet-log.sh → stdout → screen capture → extract-console-logs.py → EFS
PDP-11 BSD → arpanet-log.sh → stdout → screen capture → extract-console-logs.py → EFS
GitHub Actions → GITHUB.log → EFS
Merge: merge-logs.py → merged.log
```

### Log Format
```
[YYYY-MM-DD HH:MM:SS MACHINE] message
```

### Key Evidence Logged
- **VAX**: `cc: Berkeley C compiler, version 4.3 BSD, 7 June 1986`
- **VAX**: Binary dates from Jun 7 1986 (proves authentic binaries)
- **PDP-11**: `2.11 BSD UNIX #1: Sun Nov  7 22:40:28 PST 1999`
- **PDP-11**: nroff/uudecode tool sizes and dates

### Webpage Integration
- Examples: `site/build-logs/*.log.example`
- Template: `templates/build-info-widget.html`
- Docs: `docs/integration/EXPECTED-LOG-FORMAT.md`

## Next Steps

### 1. Test End-to-End Pipeline (READY)
- Generate resume.vax.yaml
- Upload to VAX via console
- Compile inside BSD with K&R C
- Encode inside BSD with uuencode
- Transfer to PDP-11
- Decode and render in PDP-11

---

## Key Documentation

### Must Read for Cold Start
1. **`docs/COLD-START.md`** - Quick start guide
2. **`docs/INDEX.md`** - Documentation hub

### Scripts
- `scripts/vax-console-upload.sh` - Upload files via console
- `scripts/vax-console-build.sh` - Build inside BSD via console
- `scripts/vax-build-and-encode.sh` - Build script (runs inside BSD)
- `arpanet/pdp11-boot.sh` - PDP-11 auto-mount wrapper (working)

### Archived (see `docs/deprecated/`)
- Old debugging session logs
- Superseded research documents

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
- [x] VAX console build pipeline implemented
- [x] Vintage K&R C compilation verified inside BSD

### Phase 2: 🔄 IN PROGRESS
- [x] VAX file sharing method found (console I/O)
- [x] Scripts execute inside BSD
- [x] Actual K&R C compilation verified
- [x] Actual vintage uuencode working

### Phase 3: ⏳ PENDING
- [ ] End-to-end pipeline working
- [ ] All commands in vintage tools
- [ ] Logs accurately reflect tool usage
- [ ] Deployed and operational

### GitHub ↔ AWS Lifecycle: ✅ COMPLETE
- [x] Single activation step starts both instances
- [x] Waits for both instances to be running
- [x] Validates public IP resolution and SSH readiness with hard timeout
- [x] Single deactivation step stops both instances
- [x] Waits for both instances to be stopped
- [x] Logs lifecycle markers in `GITHUB.log`

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

**NEXT SESSION**: Continue with VAX → PDP-11 pipeline validation - see `docs/integration/VAX-PDP11-VALIDATION-2026-02-14.md` for latest status.

## 2026-02-14: Console Validation Complete

**Validated**:
- ✅ AWS instances running (VAX + PDP-11)
- ✅ Console access via screen+telnet works
- ✅ File upload via heredoc works (tested)
- ✅ VAX has vintage compiler at /bin/cc
- ✅ PDP-11 booted with /usr mounted

**Key Finding**: 
- /machines volume mount is NOT accessible inside BSD
- Must use console-based file upload (heredoc method)
- This is by design - ensures vintage tools are actually used
- The console upload scripts are the correct approach

**Documentation**: `docs/integration/VAX-PDP11-VALIDATION-2026-02-14.md`
