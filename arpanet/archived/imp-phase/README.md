# IMP Phase Architecture - Archived

**Date Archived**: 2026-02-13
**Reason**: Interface incompatibility between Ethernet/TCP-IP and ARPANET 1822 protocol
**Status**: Phase 1 & 2 were validated and working, but not needed for VAX ↔ PDP-11

---

## What This Was

ARPANET Phase 1 and Phase 2 implementations using Interface Message Processors (IMPs) for routing between hosts using the historical ARPANET 1822 protocol.

**Architecture:**
```
VAX (172.20.0.10) ← Ethernet/IP
  ↕ Protocol translation
IMP #1 (172.20.0.20) ← ARPANET 1822 protocol
  ↕ IMP-to-IMP routing
IMP #2 (172.20.0.30) ← ARPANET 1822 protocol
  ↕ Protocol translation
PDP-10 (172.20.0.40) ← ARPANET 1822 interface
```

**Status**: Both phases validated as working (2026-02-07, 2026-02-08)

---

## Why Archived

**Problem**: Protocol mismatch
- VAX has native Ethernet with TCP/IP stack (BSD)
- PDP-11 has native Ethernet with TCP/IP stack (2.11BSD)
- IMPs use ARPANET 1822 protocol
- Bridging requires complex protocol translation

**Solution**: Direct TCP/IP connection
- VAX and PDP-11 both have Ethernet
- Both run BSD with native TCP/IP
- Can communicate directly via IP on Docker network
- Simpler, more reliable, no translation needed

**Precedent**: Panda PDP-10 approach successfully used TCP/IP direct path

---

## Archived Files

### Docker Images
- `Dockerfile.imp` - H316 IMP simulator build

### Configurations
- `configs/imp1.ini` - IMP #1 configuration (Phase 1)
- `configs/imp2.ini` - IMP #2 configuration (Phase 2)
- Various phase-specific configs

### Docker Compose
- `docker-compose.arpanet.phase1.yml` - VAX + IMP #1
- `docker-compose.arpanet.phase2.yml` - VAX + IMP #1 + IMP #2 + PDP-10

---

## Historical Significance

The IMP phases demonstrated:
- ✅ ARPANET 1822 protocol implementation
- ✅ Multi-hop routing through IMPs
- ✅ H316 simulator functionality
- ✅ Protocol debugging and validation
- ✅ Centralized logging system

This work validated the technical feasibility of ARPANET protocol simulation and provided valuable learning about historical networking protocols.

---

## Documentation

Related documents (also archived):
- `docs/arpanet/PHASE1-VALIDATION.md`
- `docs/arpanet/PHASE1-SUCCESS.txt`
- Memory: ARPANET Phase 1 & 2 sections

---

## If You Need This Again

The IMP implementation is fully functional and can be restored:

1. Copy files from this archive
2. Use the phase docker-compose files
3. Follow the topology generation: `arpanet-topology phase1` or `phase2`
4. Documentation in `docs/arpanet/`

**Use Cases:**
- Historical ARPANET protocol demonstration
- Systems without native TCP/IP (need 1822 translation)
- Educational purposes (show protocol evolution)
- Protocol bridging research

---

**Current Approach**: VAX ↔ PDP-11 direct TCP/IP (no IMPs)
**Production File**: `docker-compose.production.yml`
