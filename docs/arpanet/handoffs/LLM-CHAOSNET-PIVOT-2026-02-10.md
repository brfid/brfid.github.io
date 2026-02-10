# Chaosnet Pivot: PDP-10 ITS Networking Resolution (Research LLM Handoff)

**Date**: 2026-02-10  
**Repo**: `brfid.github.io`  
**Scope**: Phase 3 PDP-10 networking path decision  
**Decision**: Retire IMP/1822 path for PDP-10, proceed with Chaosnet (CH11)

---

## 1) Executive Summary: Protocol Mismatch Root Cause

After extensive analysis of the PDP-10 ↔ IMP2 host-link path, we have identified a **fundamental protocol incompatibility** that makes the current IMP-based approach permanently non-functional for host-to-host file transfer:

**The SIMH `pdp10-ks` IMP device is not an ARPANET 1822 Interface Message Processor interface.** It is a **modern Ethernet/IP network interface** that SIMH exposes to the guest OS with the internal label "IMP".

### Evidence Summary

1. **Device behavior is Ethernet/IP-oriented**:
   - Uses MAC addresses and ARP tables
   - Has DHCP/IP/gateway configuration
   - Emits Ethernet frames (confirmed by packet captures)
   - Commands: `set imp enabled`, `set imp ip`, `set imp gw`, `set imp dhcp/nodhcp`

2. **Packet capture evidence** (PDP-10 → IMP2 UDP/2000):
   ```
   0x0030: ffff ffff ffff 0000 0219 9e8f 0806 0001
   0x0040: 0800 0604 0001 0000 0219 9e8f ac14 0028
   ```
   - `0806 0001 0800 0604` = Ethernet ARP packet structure
   - The "bad magic" values in IMP2 logs (`feffffff`, `00000219`, `ffffffff`) were Ethernet frame headers being misinterpreted by H316 IMP's HI1 1822 parser

3. **The hi1shim adapter is a semantic dead-end**:
   - Shim fixed the envelope formatting (magic number accepted → `bad_magic_total_delta=0`)
   - But the **payload inside** the envelope is still an Ethernet frame, not an 1822 host message
   - IMP2 cannot route Ethernet frames through its ARPANET routing table
   - "Green" dual-window gates = syntactic success, but no host-level route is created

### Why TCP/IP FTP to `172.20.0.40:21` Will Never Work

1. **ITS uses NCP, not TCP/IP** — ARPANET's original Network Control Program
2. **ARPANET uses host/IMP octal numbering, not IP addresses** — `172.20.0.40` is meaningless to IMP2's routing layer
3. **The KS10 "IMP" device speaks Ethernet, not 1822** — fundamental protocol family mismatch

**Consequence**: No amount of configuration tuning or adapter development will bridge this gap without rewriting major components of either the SIMH KS10 emulator or the H316 IMP firmware.

---

## 2) Path Forward: Chaosnet via CH11

### Why Chaosnet

The PDP-10/ITS KS10 build from `PDP-10/its` (used in `arpanet/Dockerfile.pdp10-its`) includes the **CH11 Chaosnet interface**, which was the networking protocol MIT ITS actually used historically.

**Key facts**:
- CH11 is natively supported by the SIMH KS10 emulator
- ITS has Chaosnet drivers and file transfer services (CFTP) built into the disk image
- CH11 can be attached via TCP bridge between SIMH instances
- Chaosnet is **more historically authentic** for MIT ITS than ARPANET (MIT machines used Chaosnet for inter-machine communication)

**Configuration syntax**:
```ini
set ch enabled
attach ch listen:PORT          ; For server/bridge mode
attach ch connect:HOST:PORT    ; For client mode
```

### Historical Context

MIT's ITS machines were connected via Chaosnet, not ARPANET. The ARPANET connection was primarily for gateway access to other sites, not for local file transfer. Using Chaosnet is therefore more authentic to the historical MIT computing environment than forcing an ARPANET path.

**Reference**: MIT AI Memo 628 documents Chaosnet protocol and its use in ITS.

---

## 3) Implementation Plan

### Step 1: Verify CH11 Device Availability

Confirm CH11 is available in current pdp10-ks build:

```bash
# Check device support
docker exec arpanet-pdp10 pdp10-ks --help | grep -i "ch\|chaos"

# Or check at SIMH prompt after boot
# At sim> prompt: show devices
# Look for CH or CHAOS device listing
```

### Step 2: Update PDP-10 SIMH Configuration

Modify `arpanet/configs/phase2/pdp10.ini` to enable CH11:

```ini
; Enable Chaosnet interface
set ch enabled
attach ch listen:4001
```

**Decision**: Keep or remove IMP configuration depending on whether we want to demonstrate the dead-end path in the final artifact. Recommendation: remove IMP config to clean up the runtime.

### Step 3: Create Chaosnet Bridge/Gateway Container

Options:
1. **Second ITS instance** as Chaosnet peer for testing (simplest)
2. **Chaosnet bridge container** that connects CH11 to modern network (if needed for future expansion)
3. **Direct CH11 connection** between containers via TCP bridge

Initial recommendation: Option 1 (second ITS instance) for proof-of-concept.

Add to `docker-compose.arpanet.phase2.yml`:
```yaml
  pdp10-its-peer:
    build:
      context: ./arpanet
      dockerfile: Dockerfile.pdp10-its
    container_name: arpanet-pdp10-peer
    networks:
      arpanet:
        ipv4_address: 172.20.0.45
    ports:
      - "2327:2323"  # Console
      - "10005:10004"  # ITS user lines
    volumes:
      - ./arpanet/configs/phase2/pdp10-peer.ini:/machines/pdp10.ini:ro
    command: ["/usr/local/bin/pdp10-ks", "/machines/pdp10.ini"]
```

Create `arpanet/configs/phase2/pdp10-peer.ini`:
```ini
set ch enabled
attach ch connect:172.20.0.40:4001
; ... rest of standard ITS boot config
```

### Step 4: Boot and Verify Chaosnet Interface

After updating configs and rebuilding:

```bash
# Rebuild and start
docker compose -f docker-compose.arpanet.phase2.yml up -d --build

# Check PDP-10 console
docker logs arpanet-pdp10 --tail 100

# Connect to ITS and verify Chaosnet
telnet localhost 2326

# At ITS prompt, check Chaosnet status:
:SYSTAT   ; System status
:HOSTAT   ; Host status - should show Chaosnet hosts
```

### Step 5: Test CFTP File Transfer

Once both ITS instances are running with Chaosnet enabled:

```bash
# From primary ITS instance, transfer a file via CFTP
# (Exact commands depend on ITS CFTP syntax, typically)
:CFTP target-host
:GET remote-file local-file
:PUT local-file remote-file
```

Alternative: Use ITS SUPDUP or other Chaosnet services to validate connectivity.

---

## 4) Acceptance Criteria

Blocker considered resolved when:

1. **CH11 device verified available** in current SIMH build
2. **Chaosnet interface comes up** in ITS after configuration changes (visible in `:SYSTAT` or `:HOSTAT`)
3. **Chaosnet connectivity established** between two ITS instances or to a bridge
4. **CFTP file transfer succeeds** (or equivalent Chaosnet-based transfer validated)
5. **No regression** in VAX + IMP1 + IMP2 ARPANET infrastructure (remains operational for VAX-side work)

---

## 5) What Remains Valid from Previous Work

### Keep These Components

1. **VAX + IMP1 + IMP2 routing infrastructure** — fully operational, validated, historically authentic
2. **ARPANET 1822 protocol implementation** — works correctly for VAX ↔ IMP path
3. **Logging and monitoring systems** — valuable for both ARPANET and future Chaosnet work
4. **Console automation** — applies to all SIMH-based systems
5. **Evidence collection workflow** — continue using for validation

### Retire These Components for PDP-10 Path

1. **hi1shim** (Host-IMP Interface adapter) — no longer needed; was a syntactic-only fix
2. **PDP-10 IMP configuration** — fundamentally incompatible; replace with CH11
3. **IMP2 HI1 → PDP-10 host-link** — cannot route Ethernet frames through 1822 IMP
4. **Dual-window HI1 gate tests for PDP-10** — validated the wrong layer; retire for PDP-10 (keep for VAX)
5. **FTP to `172.20.0.40:21` expectation** — wrong protocol family; use CFTP instead

### Documentation to Preserve

Keep all handoff documents as historical record:
- `LLM-HOST-LINK-BLOCKER-2026-02-09.md` — documents the discovery process
- `LLM-PDP10-FTP-BLOCKER-2026-02-10.md` — shows the endpoint readiness investigation
- This document — explains the pivot decision

---

## 6) Updated Architecture

### New Topology

```
ARPANET Side:
[VAX/BSD] ↔ [IMP #1] ↔ [IMP #2]
  (1822 protocol, historically authentic)

Chaosnet Side:
[PDP-10/ITS] ↔ [Chaosnet Bridge or Peer ITS]
  (Chaosnet protocol, historically authentic for MIT)
```

This is **more historically accurate** than the original plan:
- MIT ITS machines used Chaosnet for local networking
- ARPANET was used for gateway/remote access, not local file transfer
- VAX on ARPANET demonstrates DEC/BSD authentic networking
- PDP-10 on Chaosnet demonstrates MIT ITS authentic networking

### Final Pipeline Concept

For the resume build pipeline:
1. **VAX compiles source code** (authentic 1980s BSD development environment)
2. **VAX transfers to ITS via ARPANET→Chaosnet gateway** (if needed) OR
3. **Separate demonstration**: VAX on ARPANET + PDP-10 on Chaosnet as parallel historical computing showcases

The "quiet technical signal" is strengthened: demonstrating **two authentic historical network protocols** rather than forcing an inauthentic hybrid.

---

## 7) Risk Mitigation

### Technical Risks

1. **CH11 not available in current build**
   - Mitigation: Check early (Step 1); if missing, use different ITS build or emulator version
   - Fallback: Document findings and keep VAX ARPANET path as primary showcase

2. **CFTP configuration complex**
   - Mitigation: Use ITS documentation and SIMH community resources
   - Start with simple connectivity test before file transfer

3. **Two-protocol demo adds complexity**
   - Mitigation: This is actually simpler than forcing incompatible protocols together
   - Each protocol is authentic and self-contained

### Schedule Risks

1. **Learning Chaosnet takes time**
   - Mitigation: Chaosnet is simpler than ARPANET; ITS has it built-in
   - Community resources available (Chaosnet documentation, ITS manuals)

2. **Two networks to maintain**
   - Mitigation: They're independent; Chaosnet doesn't affect validated ARPANET work
   - Can demonstrate ARPANET-only first, add Chaosnet later

---

## 8) Decision Rationale: Why Now

### Authenticity-First Principle

Per project guidelines (from `docs/COLD-START.md` and `STATUS.md`), the goal is historical authenticity. Forcing Ethernet-over-ARPANET violates this principle. Using Chaosnet for ITS is **more authentic** than any IMP-based workaround.

### Technical Dead-End Confirmed

The evidence is conclusive:
- Packet captures show Ethernet frames, not 1822 messages
- Protocol families are incompatible (L2 vs L3 semantics)
- No configuration change can bridge this gap
- Adapter development would require protocol translation, not simple framing fixes

### Cost-Benefit Analysis

**Cost of continuing IMP path**:
- Complex protocol translator (hundreds of lines of code)
- Ongoing maintenance burden
- Fundamentally inauthentic to both protocols
- No historical precedent for this hybrid

**Cost of Chaosnet pivot**:
- Learn Chaosnet configuration (well-documented)
- Update PDP-10 configs (simple)
- Add bridge or peer container (straightforward)
- **Benefit**: Historically authentic, simpler, self-documenting

**Decision**: Pivot to Chaosnet.

---

## 9) Next Actions (Command-First)

### Immediate (Day 1)

```bash
# 1. Verify CH11 availability
docker exec arpanet-pdp10 pdp10-ks --help | grep -i "ch\|chaos"

# 2. Research ITS Chaosnet commands (if not already known)
# Check MIT ITS documentation for CFTP/Chaosnet usage

# 3. Update documentation (this handoff + NEXT-STEPS.md + STATUS.md)
```

### Short-term (Week 1)

```bash
# 4. Update pdp10.ini with CH11 config
# Edit arpanet/configs/phase2/pdp10.ini

# 5. Create peer ITS config or bridge design
# Add to docker-compose.arpanet.phase2.yml

# 6. Rebuild and test
docker compose -f docker-compose.arpanet.phase2.yml build pdp10
docker compose -f docker-compose.arpanet.phase2.yml up -d

# 7. Verify Chaosnet interface comes up
docker logs arpanet-pdp10 --tail 100 | grep -i "ch\|chaos"
```

### Medium-term (Week 2-3)

```bash
# 8. Test CFTP or equivalent transfer
# Document exact commands after ITS Chaosnet research

# 9. Update PHASE3-PROGRESS.md with results

# 10. Create CHAOSNET-INTEGRATION.md guide for future maintainers
```

---

## 10) References

### SIMH Documentation
- SIMH User's Guide: CH11 Chaosnet configuration syntax
- SIMH GitHub: `PDP-10/its` repository with CH11-enabled builds

### Historical Documentation
- MIT AI Memo 628: Chaosnet protocol specification
- ITS documentation: Chaosnet services and CFTP usage
- MIT AI Lab history: Chaosnet as the primary local network

### Project Documentation
- `docs/arpanet/handoffs/LLM-HOST-LINK-BLOCKER-2026-02-09.md` — HI1 framing investigation
- `docs/arpanet/handoffs/LLM-PDP10-FTP-BLOCKER-2026-02-10.md` — Service readiness investigation
- `STATUS.md` — Current project status and blockers
- `docs/arpanet/progress/NEXT-STEPS.md` — Active task list

---

## 11) Conclusion

The PDP-10 IMP/1822 path is **permanently retired** as of 2026-02-10 due to fundamental protocol incompatibility (Ethernet vs 1822). The project proceeds with **Chaosnet (CH11)** for PDP-10 networking, which is:

1. **Technically feasible** — built into ITS and SIMH
2. **Historically authentic** — MIT ITS's actual networking protocol
3. **Simpler** — no protocol translation needed
4. **Self-documenting** — demonstrates two authentic historical networks

The VAX + IMP1 + IMP2 ARPANET infrastructure remains **fully operational and validated** for the BSD/VAX portion of the project. The final architecture demonstrates both ARPANET (DEC/BSD) and Chaosnet (MIT/ITS) as parallel authentic historical computing showcases.

**Status**: Documentation updated; implementation begins with CH11 verification.  
**Timeline**: 1-2 weeks for Chaosnet integration and testing.  
**Risk**: Low — proven technology with historical precedent.
