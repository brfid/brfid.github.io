# PDP-10 TOPS-20 Testing Log

**Date**: 2026-02-07
**Goal**: Validate PDP-10 TOPS-20 container build and integration with ARPANET Phase 2

---

## Test Environment

**Platform**: AWS EC2 (x86_64)
- Instance: 34.227.223.186 (i-0568f075e84bf24dd)
- Type: t3.medium
- OS: Ubuntu 22.04
- Docker: Latest
- Architecture: x86_64 (required for SIMH compatibility)

---

## Test Sequence

### Test 1: PDP-10 Container Build

**Status**: In progress

**Command**:
```bash
ssh ubuntu@34.227.223.186
cd brfid.github.io
git pull
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
```

**Expected Behavior**:
1. Dockerfile.pdp10 builder stage:
   - Install build dependencies
   - Clone SIMH from GitHub
   - Compile pdp10-ks emulator
   - Download TOPS-20 V4.1 tape from pdp-10.trailing-edge.com
   - Extract from bz2 compression

2. Runtime stage:
   - Copy pdp10-ks binary
   - Copy TOPS-20 tape
   - Set up directories
   - Create final image

**Success Criteria**:
- Build completes without errors
- Image tagged as `arpanet-pdp10`
- TOPS-20 tape present at `/machines/pdp10/tops20_v41.tap`
- pdp10-ks binary at `/usr/local/bin/pdp10-ks`

### Test 2: Full Phase 2 Stack Startup

**Status**: Pending

**Command**:
```bash
docker compose -f docker-compose.arpanet.phase2.yml up -d
docker compose -f docker-compose.arpanet.phase2.yml ps
```

**Expected Containers**:
- arpanet-vax (172.20.0.10:2323)
- arpanet-imp1 (172.20.0.20:2324)
- arpanet-imp2 (172.20.0.30:2325)
- arpanet-pdp10 (172.20.0.40:2326)

**Success Criteria**:
- All 4 containers start and stay running
- No crash loops
- Network connectivity visible in logs

### Test 3: PDP-10 Console Access

**Status**: Pending

**Command**:
```bash
telnet localhost 2326
```

**Expected Behavior**:
- Connect to PDP-10 SIMH console
- See TOPS-20 boot messages
- Reach installation prompt or boot loader

**Success Criteria**:
- Telnet connection established
- SIMH pdp10-ks banner visible
- TOPS-20 boot sequence starts

### Test 4: Network Interface Validation

**Status**: Pending

**Check**:
1. IMP #2 logs for DTE/HI1 activity
2. PDP-10 console for network messages
3. Docker network stats

**Commands**:
```bash
docker logs arpanet-imp2 | grep -i "HI1\|host\|dte"
docker logs arpanet-pdp10 | grep -i "dte\|network"
docker network inspect arpanet-build
```

**Success Criteria**:
- IMP #2 shows PDP-10 host connection (not stub probes)
- DTE interface attached to 172.20.0.40:2000
- Bidirectional UDP traffic visible

### Test 5: Multi-Hop Routing

**Status**: Pending

**Goal**: Verify packet flow VAX → IMP1 → IMP2 → PDP-10

**Method**:
- Enable debug on all IMPs
- Generate test traffic from VAX
- Monitor IMP routing logs
- Check PDP-10 receives packets

**Success Criteria**:
- Packets route through both IMPs
- No routing loops
- PDP-10 receives ARPANET protocol messages

### Test 6: TOPS-20 Installation

**Status**: Pending (manual step)

**Process**:
1. Connect to PDP-10 console (telnet localhost 2326)
2. Boot from installation tape (tu0)
3. Follow TOPS-20 V4.1 installation wizard
4. Create system disk on rp0
5. Configure networking
6. Set up user accounts
7. Enable FTP daemon

**Duration**: ~1-2 hours

**Note**: This is a one-time setup. Disk image will be preserved.

---

## Results

### Build Test (Test 1)

**Status**: Running...

**Timeline**:
- 21:51 UTC: AWS instance created
- 21:55 UTC: SSH connection established
- 21:56 UTC: PDP-10 container build started
- ... (waiting for completion)

**Logs**: (to be captured)

---

## Issues Encountered

### Issue 1: (if any)

**Description**: TBD

**Resolution**: TBD

---

## Next Steps After Testing

1. **If build succeeds**:
   - Start full Phase 2 stack
   - Access PDP-10 console
   - Install TOPS-20
   - Configure networking
   - Test FTP

2. **If build fails**:
   - Review error logs
   - Check TOPS-20 tape download
   - Verify SIMH compilation
   - Debug Dockerfile

3. **Documentation**:
   - Update PHASE2-STEP2.2-PDP10.md with results
   - Create validation report
   - Document installation steps
   - Update README.md

---

**Status**: Testing in progress
**Last Updated**: 2026-02-07 21:56 UTC
