# ARPANET Phase 2 Plan: Multi-Hop Network Topology

**Status**: In Progress (Step 2.1 complete, Step 2.2 bootstrap underway)
**Prerequisite**: Phase 1 Complete ✅
**Goal**: Establish two-IMP network with multi-hop routing and file transfer capability

---

## Overview

Phase 2 expands the ARPANET infrastructure from a single VAX-IMP connection to a full multi-hop network with two IMPs and two hosts, enabling authentic ARPANET packet routing and file transfer.

## Architecture

### Network Topology

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   VAX/BSD   │ Host    │   IMP #1    │ Modem   │   IMP #2    │ Host    │  PDP-10/ITS │
│ 172.20.0.10 │◄───────►│ 172.20.0.20 │◄───────►│ 172.20.0.30 │◄───────►│ 172.20.0.40 │
│             │   HI1   │             │   MI1   │             │   HI1   │             │
│ ARPANET #1  │         │  Site #1    │         │  Site #2    │         │ ARPANET #65 │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
      :2323                  :2324                   :2325                   :2326
```

### IP Addressing (Docker Network: 172.20.0.0/16)

| Component | IP Address | Container Name | Console Port |
|-----------|------------|----------------|--------------|
| VAX/BSD | 172.20.0.10 | arpanet-vax | 2323 |
| IMP #1 | 172.20.0.20 | arpanet-imp1 | 2324 |
| IMP #2 | 172.20.0.30 | arpanet-imp2 | 2325 |
| PDP-10 | 172.20.0.40 | arpanet-pdp10 | 2326 |

### ARPANET Addresses

| Host | ARPANET Octal Address | Site Name | OS |
|------|----------------------|-----------|-----|
| VAX | 001 (octal) | Site #1 | BSD 4.3 |
| PDP-10 | 101 (octal) | Site #65 | ITS or TOPS-20 |

---

## Components

### 1. Existing (Phase 1)

- ✅ VAX/BSD container with network interface
- ✅ IMP #1 with Host Interface 1 (HI1) to VAX
- ✅ Docker network (arpanet-build: 172.20.0.0/16)

### 2. New Components (Phase 2)

#### IMP #2 Container
**Purpose**: Second IMP router for multi-hop packet switching
**Configuration**:
- SIMH H316 simulator (same as IMP #1)
- Host Interface 1 (HI1): Connection to PDP-10 via UDP port 2000
- Modem Interface 1 (MI1): Connection to IMP #1 via UDP port 3001
- IMP number: 2
- Site identifier: #2

**Files**:
- `arpanet/Dockerfile.imp` (reuse existing)
- `arpanet/configs/imp2.ini` (new configuration)

#### PDP-10 Container
**Purpose**: Second host for file transfer testing
**Options**:
1. **ITS (Incompatible Timesharing System)** - MIT AI Lab OS
   - More authentic for 1970s ARPANET
   - Smaller footprint
   - SIMH pdp10-ka emulator
2. **TOPS-20** - DEC production OS
   - Better documented
   - Easier file transfer setup
   - SIMH pdp10-ks emulator

**Recommendation**: Start with TOPS-20 for easier debugging, migrate to ITS in Phase 3 if desired.

**Configuration**:
- SIMH PDP-10 emulator
- Network interface attached to IMP #2 via UDP
- FTP daemon for file transfer
- ARPANET host software

**Files**:
- `arpanet/Dockerfile.pdp10` (new)
- `arpanet/configs/pdp10.ini` (new)

---

## Implementation Steps

### Step 1: IMP-to-IMP Communication (Modem Interfaces)

**Objective**: Enable packet routing between IMP #1 and IMP #2

**Tasks**:
1. Update `arpanet/configs/imp-phase1.ini` → `imp1-phase2.ini`
   - Enable Modem Interface 1 (MI1)
   - Configure: `attach -u mi1 3001:172.20.0.30:3001`
   - Set IMP #2 as neighbor

2. Create `arpanet/configs/imp2.ini`
   - Set IMP number: `set imp num=2`
   - Enable Host Interface 1: connection to PDP-10
   - Enable Modem Interface 1: connection to IMP #1
   - Configure: `attach -u mi1 3001:172.20.0.20:3001`

3. Update `docker-compose.arpanet.phase2.yml`
   - Add imp2 service
   - Assign IP 172.20.0.30
   - Map console to port 2325
   - Configure UDP ports for modem (3001) and host (2000) interfaces

**Success Criteria**:
- Both IMPs start without errors
- IMP logs show modem interface enabled and connected
- Routing table updates on both IMPs
- Ping between IMPs (if available) or packet exchange visible in debug logs

**Current Result (2026-02-07, AWS x86_64)**: ✅ Complete
- `docker-compose.arpanet.phase2.yml` validated with `arpanet-vax`, `arpanet-imp1`, `arpanet-imp2`
- `arpanet/scripts/test-phase2-imp-link.sh` passes
- MI1 packet send/receive confirmed in both IMP logs

**Step 2.2 bootstrap update (2026-02-07, AWS x86_64)**: 🟡 In progress
- Added `arpanet-pdp10` host stub at `172.20.0.40`
- Wired IMP2 HI1 attach to `172.20.0.40:2000`
- Observed IMP2 HI1 transmit markers in logs
- Full PDP-10 OS image/integration remains pending

### Step 2: PDP-10 Host Setup

**Objective**: Add second host to the network

**Tasks**:
1. Research PDP-10 SIMH images:
   - Check available TOPS-20 disk images
   - Verify network support in SIMH pdp10 emulator
   - Identify FTP implementation

2. Create `arpanet/Dockerfile.pdp10`:
   - Base image: Debian/Alpine with build tools
   - Clone and build SIMH pdp10 emulator
   - Download/mount TOPS-20 disk image
   - Configure network interface

3. Create `arpanet/configs/pdp10.ini`:
   - Load TOPS-20 disk
   - Configure network interface
   - Attach to IMP #2 via UDP port 2000
   - Set ARPANET host address (octal 101)

4. Update `docker-compose.arpanet.phase2.yml`:
   - Add pdp10 service
   - Assign IP 172.20.0.40
   - Map console to port 2326
   - Volume mount for disk images

**Success Criteria**:
- PDP-10 boots to TOPS-20 prompt
- Network interface detected
- IMP #2 logs show host connection
- Can login to PDP-10 via telnet

### Step 3: Multi-Hop Routing Test

**Objective**: Verify packet routing across both IMPs

**Tasks**:
1. Enable ARPANET protocol debugging on both IMPs
2. Generate test traffic from VAX
3. Monitor IMP logs for:
   - Packet arrival at IMP #1
   - Routing decision (forward to IMP #2)
   - Packet transmission on modem interface
   - Receipt at IMP #2
   - Delivery to PDP-10

4. Verify routing tables:
   - IMP #1 knows route to host 101 (via IMP #2)
   - IMP #2 knows route to host 1 (via IMP #1)

**Success Criteria**:
- Packets successfully routed from VAX through IMP #1 → IMP #2 → PDP-10
- No routing loops or dropped packets
- RFNM (Ready For Next Message) acknowledgments returned
- Round-trip packet flow confirmed

### Step 4: File Transfer Test

**Objective**: Transfer a file from VAX to PDP-10 using ARPANET FTP

**Tasks**:
1. Create test file on VAX:
   ```bash
   echo "ARPANET Phase 2 Test" > /tmp/test.txt
   ```

2. Configure FTP on both systems:
   - VAX: BSD FTP client (already available)
   - PDP-10: TOPS-20 FTP server

3. Attempt FTP connection from VAX to PDP-10:
   ```bash
   ftp 172.20.0.40  # Or ARPANET address if configured
   ```

4. Transfer test file

5. Verify file contents on PDP-10

**Success Criteria**:
- FTP connection established
- File transferred successfully
- Content verification matches
- Transfer logged in IMP debug output
- No packet loss or retransmissions

### Step 5: Documentation

**Objective**: Document Phase 2 implementation and results

**Tasks**:
1. Create `arpanet/PHASE2-SUMMARY.md`
   - Architecture overview
   - Configuration details
   - Testing results

2. Create `arpanet/PHASE2-VALIDATION.md`
   - Detailed test results
   - IMP routing logs
   - File transfer transcript
   - Performance metrics

3. Update `arpanet/README.md`:
   - Add Phase 2 usage instructions
   - Update development status
   - Document new docker-compose commands

4. Create `arpanet/scripts/test-multi-hop.sh`:
   - Automated testing for Phase 2
   - Checks all four containers
   - Tests routing between IMPs
   - Validates file transfer

**Deliverables**:
- Complete Phase 2 documentation
- Test scripts for validation
- Build logs showing successful multi-hop transfer

---

## Docker Compose Structure

### File: `docker-compose.arpanet.phase2.yml`

```yaml
version: '3.8'

services:
  vax:
    # (unchanged from Phase 1)
    image: jguillaumes/simh-vaxbsd@sha256:1bab805b25a793...
    container_name: arpanet-vax
    networks:
      arpanet:
        ipv4_address: 172.20.0.10
    ports:
      - "2323:2323"

  imp1:
    # (updated for Phase 2)
    build:
      context: ./arpanet
      dockerfile: Dockerfile.imp
    container_name: arpanet-imp1
    networks:
      arpanet:
        ipv4_address: 172.20.0.20
    volumes:
      - ./arpanet/configs/imp1-phase2.ini:/machines/imp.ini:ro
      - ./arpanet/configs/impcode.simh:/machines/impcode.simh:ro
      - ./arpanet/configs/impconfig.simh:/machines/impconfig.simh:ro
    environment:
      - IMP_NUMBER=1
      - HOST_LINK_0=172.20.0.10:2000
      - MODEM_LINK_1=172.20.0.30:3001
    ports:
      - "2324:2323"

  imp2:
    # (new for Phase 2)
    build:
      context: ./arpanet
      dockerfile: Dockerfile.imp
    container_name: arpanet-imp2
    networks:
      arpanet:
        ipv4_address: 172.20.0.30
    volumes:
      - ./arpanet/configs/imp2.ini:/machines/imp.ini:ro
      - ./arpanet/configs/impcode.simh:/machines/impcode.simh:ro
      - ./arpanet/configs/impconfig.simh:/machines/impconfig.simh:ro
    environment:
      - IMP_NUMBER=2
      - HOST_LINK_0=172.20.0.40:2000
      - MODEM_LINK_1=172.20.0.20:3001
    ports:
      - "2325:2323"
    depends_on:
      - imp1

  pdp10:
    # (new for Phase 2)
    build:
      context: ./arpanet
      dockerfile: Dockerfile.pdp10
    container_name: arpanet-pdp10
    networks:
      arpanet:
        ipv4_address: 172.20.0.40
    volumes:
      - ./arpanet/configs/pdp10.ini:/machines/pdp10.ini:ro
      - ./build/arpanet/pdp10:/machines/data
    ports:
      - "2326:2323"
    depends_on:
      - imp2

networks:
  arpanet:
    name: arpanet-build
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
          gateway: 172.20.0.1
```

---

## Technical Challenges

### Challenge 1: IMP Routing Table Initialization

**Issue**: IMPs need to know about other IMPs and hosts in the network.

**Solution**:
- Configure static routing in IMP firmware
- Use SIMH configuration commands to set neighbor relationships
- Reference obsolescence/arpanet project for routing table format

### Challenge 2: ARPANET Address Translation

**Issue**: Mapping between IP addresses and ARPANET octal addresses.

**Solution**:
- Keep IP networking at Docker layer (172.20.x.x)
- Use ARPANET addresses only within IMP firmware layer
- Document the mapping clearly

### Challenge 3: PDP-10 Network Configuration

**Issue**: PDP-10 TOPS-20 network stack may need configuration.

**Solution**:
- Research TOPS-20 networking documentation
- Check if SIMH pdp10 supports network interfaces
- Fall back to console-based file transfer if network unavailable
- Consider using TAP file format for tape-based transfer

### Challenge 4: Modem Interface Timing

**Issue**: IMP modem interfaces may require specific timing or line discipline.

**Solution**:
- Use UDP for simplicity (same as host interfaces)
- Enable debug logging on modem interfaces
- Adjust SIMH timing if packet loss occurs
- Reference SIMH H316 documentation for modem parameters

---

## Success Criteria

Phase 2 is complete when:

1. ✅ All four containers start and run stably
2. ✅ Both IMPs show modem interface connection established
3. ✅ VAX can generate packets that reach PDP-10
4. ✅ PDP-10 can generate packets that reach VAX
5. ✅ IMP routing tables show correct topology
6. ✅ File successfully transferred from VAX to PDP-10
7. ✅ No packet loss or routing errors in IMP logs
8. ✅ Documentation complete with test results

---

## Timeline Estimate

| Phase | Task | Estimated Time |
|-------|------|----------------|
| 2.1 | IMP-to-IMP modem interfaces | 2-3 hours |
| 2.2 | PDP-10 container setup | 3-4 hours |
| 2.3 | Multi-hop routing test | 1-2 hours |
| 2.4 | File transfer test | 1-2 hours |
| 2.5 | Documentation | 1-2 hours |
| **Total** | | **8-13 hours** |

*Note: Estimates assume AWS EC2 testing at ~$0.04/hour = ~$0.32-$0.52 total*

---

## Resources

### SIMH Documentation
- H316 IMP: http://simh.trailing-edge.com/pdf/h316_doc.pdf
- PDP-10: http://simh.trailing-edge.com/pdf/pdp10_doc.pdf

### ARPANET Resources
- obsolescence/arpanet: https://github.com/obsolescence/arpanet
- RFC 1822: https://tools.ietf.org/html/rfc1822
- IMP specification: BBN Report 1822

### TOPS-20 Resources
- TOPS-20 documentation: http://pdp-10.trailing-edge.com/
- SIMH PDP-10 images: http://simh.trailing-edge.com/software.html

### ITS Resources (Alternative to TOPS-20)
- ITS documentation: https://github.com/PDP-10/its
- Lars Brinkhoff's ITS: https://github.com/larsbrinkhoff/its

---

## Dependencies

### Software
- Docker (existing)
- Docker Compose (existing)
- SIMH H316 (existing, Phase 1)
- SIMH PDP-10 (new, to be built)
- TOPS-20 disk images (to be obtained)

### Knowledge
- ARPANET 1822 protocol (documented in RFC 1822)
- IMP modem interface configuration (SIMH H316 docs)
- PDP-10 networking (TOPS-20 manuals)
- SIMH configuration syntax (reference existing configs)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PDP-10 images unavailable | Low | High | Use ITS instead, or simulate with echo server |
| Modem interface incompatibility | Medium | Medium | Fall back to single-IMP topology, use host routing |
| Routing table configuration complex | Medium | Medium | Study obsolescence/arpanet configs closely |
| File transfer protocol mismatch | Medium | Low | Use simple TCP echo test instead of FTP |
| Performance issues with 4 containers | Low | Low | AWS t3.medium should handle it fine |

---

## Next Steps After Phase 2

### Phase 3: Build Pipeline Integration

Once Phase 2 is validated, integrate ARPANET into the actual build pipeline:

1. **Compile on VAX**: Build `bradman.c` on VAX
2. **Transfer via ARPANET**: Send binary from VAX → IMP #1 → IMP #2 → PDP-10
3. **Execute on PDP-10**: Run or verify the transferred artifact
4. **Return results**: Transfer output back through the network
5. **Build log**: Include complete ARPANET transfer transcript in build output

**Goal**: The resume build process depends on a working ARPANET for artifact distribution.

---

**Status**: Active implementation in progress
**Prerequisites**: ✅ Phase 1 complete and validated
**Next Action**: Replace PDP10 host stub with real PDP-10 guest (TOPS-20/ITS) and validate multi-hop host traffic

---

*Plan created: 2026-02-07*
*Phase 1 completion: 2026-02-07*
*Target start: When ready for implementation*
