# Phase 2 Step 2.2: PDP-10 TOPS-20 Integration

**Status**: In progress
**Date Started**: 2026-02-07
**Goal**: Replace PDP-10 host stub with real TOPS-20 operating system

---

## Overview

This step completes Phase 2 by integrating a real PDP-10 running TOPS-20 V4.1 into the ARPANET topology. The PDP-10 will serve as the second host, enabling file transfer testing and multi-hop routing validation.

## Architecture

```
[VAX/BSD] ←HI1→ [IMP #1] ←MI1→ [IMP #2] ←HI1→ [PDP-10/TOPS-20]
172.20.0.10    172.20.0.20   172.20.0.30      172.20.0.40
```

## Components Created

### 1. Dockerfile.pdp10

**Location**: `arpanet/Dockerfile.pdp10`

**Key Features**:
- Multi-stage build (builder + runtime)
- Compiles SIMH pdp10-ks from source
- Downloads TOPS-20 V4.1 installation tape from [pdp-10.trailing-edge.com](http://pdp-10.trailing-edge.com/tapes/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2)
- Installs runtime dependencies (telnet, expect, netcat)
- Exposes port 2323 (console) and UDP 2000 (ARPANET)

**Build Process**:
```dockerfile
# Builder stage:
- Clone SIMH from GitHub
- Build pdp10-ks emulator
- Download TOPS-20 V4.1 tape image (bb-d867e-bm_tops20_v41_2020_instl.tap.bz2)
- Extract tape from bzip2

# Runtime stage:
- Copy pdp10-ks binary
- Copy TOPS-20 installation tape
- Set up working directories
- Expose ports
```

### 2. SIMH Configuration (pdp10.ini)

**Location**: `arpanet/configs/pdp10.ini`

**Key Settings**:
```ini
; CPU and Memory
set cpu tops20v41
set cpu 4096k

; Tape Drive (installation media)
set tu0 locked
attach tu0 /machines/pdp10/tops20_v41.tap

; Disk Drive (RP06)
set rp0 rp06
attach rp0 /machines/data/tops20.dsk

; DTE Network Interface (ARPANET to IMP #2)
set dte enabled
attach -u dte 2000:172.20.0.30:2000

; Telnet Console
set console telnet=2323

; Boot from tape (first run) or disk (after install)
boot tu0
```

### 3. Docker Compose Updates

**File**: `docker-compose.arpanet.phase2.yml`

**Changes**:
- Updated header comment (removed "stub" reference)
- Changed dockerfile from `Dockerfile.pdp10stub` to `Dockerfile.pdp10`
- Added volume mounts:
  - `./build/arpanet/pdp10:/machines/data` (persistent disk storage)
  - `./arpanet/configs/pdp10.ini:/machines/pdp10.ini:ro` (SIMH config)

---

## TOPS-20 Selection Rationale

**Chosen**: TOPS-20 V4.1 with SIMH pdp10-ks

**Alternatives Considered**:
1. **ITS (Incompatible Timesharing System)**
   - More authentic to 1970s ARPANET (MIT AI Lab)
   - Smaller footprint
   - Less documentation, harder FTP setup

2. **TOPS-20 V7.0 (Panda Distribution)**
   - Newer, more features
   - Requires KL10 emulator (not standard in SIMH)
   - Larger disk images

**Why TOPS-20 V4.1**:
- ✅ Native support in SIMH pdp10-ks (standard build)
- ✅ Well-documented FTP implementation
- ✅ Compatible with ARPANET protocols
- ✅ Manageable disk size (~100-300 MB)
- ✅ Proven compatibility with VAX/BSD FTP
- ✅ Available from official sources

**Sources**:
- [Running TOPS-20 V4.1 under SIMH](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [SIMH Software Kits](https://simh.trailing-edge.com/software.html)
- [pdp-10.trailing-edge.com tapes](http://pdp-10.trailing-edge.com/)

---

## Installation Process

### Phase 1: Container Build (Current)

**Status**: ✅ Complete (files created, not yet tested)

**Tasks**:
- [x] Create Dockerfile.pdp10
- [x] Create pdp10.ini configuration
- [x] Update docker-compose.arpanet.phase2.yml
- [ ] Test build on AWS EC2 x86_64
- [ ] Validate container starts

### Phase 2: TOPS-20 Installation (Pending)

**Steps**:
1. Build and start PDP-10 container
2. Connect to console: `telnet localhost 2326`
3. Boot from installation tape (tu0)
4. Follow TOPS-20 V4.1 installation wizard
5. Create system disk on rp0
6. Configure networking (DTE interface)
7. Enable FTP daemon
8. Test basic OS functionality

**Expected Duration**: 1-2 hours (manual setup)

**Note**: This will be a one-time installation. After initial setup, disk image will be preserved in `build/arpanet/pdp10/tops20.dsk` and future boots will use `boot rp0` instead of `boot tu0`.

### Phase 3: Network Validation (Pending)

**Tests**:
1. Verify DTE interface shows up in TOPS-20
2. Check IMP #2 logs for PDP-10 host connection
3. Test basic ARPANET connectivity
4. Validate routing: VAX → IMP1 → IMP2 → PDP-10
5. Confirm bidirectional packet flow

**Success Criteria**:
- PDP-10 console accessible on port 2326
- DTE debug shows ARPANET protocol messages
- IMP #2 HI1 logs show host traffic (not just stub probes)
- No packet loss or routing errors

### Phase 4: FTP Setup (Pending)

**Tasks**:
1. Enable TOPS-20 FTP daemon
2. Create test user account
3. Configure FTP for anonymous access (or test account)
4. Test FTP from VAX to PDP-10
5. Test reverse: PDP-10 to VAX
6. Automate with expect scripts

**Test Sequence**:
```bash
# From VAX console
ftp 172.20.0.40
# Login with test credentials
put /tmp/test.txt
bye

# Verify file on PDP-10
# Return transfer
put /tmp/verification.txt

# Verify on VAX
```

---

## Technical Challenges

### Challenge 1: TOPS-20 Installation Complexity

**Issue**: TOPS-20 installation may require manual intervention and TOPS-20 knowledge.

**Mitigation**:
- Use TOPS-20 V4.1 documentation ([gunkies.org wiki](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH))
- Follow existing community installation guides
- Preserve installed disk image for reuse
- Consider pre-built disk images if available

**Status**: Not yet encountered

### Challenge 2: Network Interface Configuration

**Issue**: DTE interface may need TOPS-20-side configuration beyond SIMH attach.

**Mitigation**:
- Research TOPS-20 network configuration
- Check SIMH PDP-10 documentation for DTE usage
- Look at obsolescence/arpanet project for examples
- Enable full DTE debugging

**Status**: Configuration created, awaiting testing

### Challenge 3: FTP Daemon Setup

**Issue**: TOPS-20 FTP daemon may need setup and user accounts.

**Mitigation**:
- Reference TOPS-20 FTP documentation
- Use anonymous FTP if supported
- Create minimal test account
- Document setup steps for reproducibility

**Status**: Not yet encountered

---

## Resources

### Documentation
- [SIMH PDP-10 Manual (PDF)](http://simh.trailing-edge.com/pdf/pdp10_doc.pdf)
- [Running TOPS-20 V4.1 under SIMH - Computer History Wiki](https://gunkies.org/wiki/Running_TOPS-20_V4.1_under_SIMH)
- [Installing TOPS-20 on SIMH Discussion](https://alt.sys.pdp10.narkive.com/hwu2mdz6/installing-tops-20-on-simh)
- [TOPS-20 Archive](http://pdp-10.trailing-edge.com/)

### Code References
- `arpanet/Dockerfile.imp` - Pattern for SIMH Docker builds
- `arpanet/configs/imp2.ini` - UDP attachment pattern
- `arpanet/configs/vax-network.ini` - VAX networking example

### Disk Images
- TOPS-20 V4.1 Installation: http://pdp-10.trailing-edge.com/tapes/bb-d867e-bm_tops20_v41_2020_instl.tap.bz2
- TOPS-20 V4.1 Distribution: http://pdp-10.trailing-edge.com/tapes/bb-d868e-bm_tops20_v41_2020_dist_1of2.tap.bz2

---

## Next Steps

1. **Test on AWS EC2**:
   ```bash
   make aws-up
   make aws-ssh
   cd brfid.github.io
   docker compose -f docker-compose.arpanet.phase2.yml build pdp10
   docker compose -f docker-compose.arpanet.phase2.yml up -d
   ```

2. **Install TOPS-20**:
   - Connect to console: `telnet localhost 2326`
   - Follow installation prompts
   - Configure networking
   - Enable FTP

3. **Validate Multi-Hop**:
   - Run `arpanet/scripts/test-phase2-imp-link.sh`
   - Check all IMP logs for routing
   - Test VAX → PDP-10 connectivity

4. **Document Results**:
   - Create PHASE2-COMPLETE.md
   - Update PHASE2-VALIDATION.md with PDP-10 results
   - Update README.md status

---

## Timeline

| Phase | Task | Status | Estimated Time |
|-------|------|--------|----------------|
| 1 | Create Dockerfile + config | ✅ Complete | 1 hour |
| 2 | Test container build | Pending | 30 min |
| 3 | Install TOPS-20 | Pending | 1-2 hours |
| 4 | Configure networking | Pending | 1 hour |
| 5 | Test multi-hop routing | Pending | 1 hour |
| 6 | Setup FTP | Pending | 1-2 hours |
| 7 | Validate file transfer | Pending | 1 hour |
| 8 | Documentation | Pending | 1 hour |
| **Total** | | | **7-10 hours** |

**AWS Cost Estimate**: ~$0.28-$0.40 at $0.04/hour

---

**Status**: Phase 1 complete, ready for AWS testing
**Next Action**: Deploy to AWS EC2 and test PDP-10 container build
**Updated**: 2026-02-07
