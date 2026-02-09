# PDP-10 ↔ IMP2 Host-Link Blocker (Research LLM Handoff)

**Date**: 2026-02-09  
**Scope**: Phase 3 host-to-host milestone (VAX ↔ IMP1 ↔ IMP2 ↔ PDP-10/ITS)  
**Environment**: AWS EC2 x86_64 (`ubuntu@34.227.223.186`), Docker Compose Phase 2

---

## 1) Executive Summary

The system has moved past the original PDP-10 boot loop and now reaches a stable runtime (`DSKDMP`). IMP1↔IMP2 modem traffic is healthy, and IMP2 host-link checks pass at a coarse startup-marker level. However, true host-level exchange between IMP2 and PDP-10 is blocked by a **protocol/framing mismatch**:

- IMP2 reports on HI1:
  - `HI1 UDP: link 1 - received packet w/bad magic number (magic=feffffff)`
  - `... (magic=00000219)`
  - `... (magic=ffffffff)`

This indicates packets arriving at IMP2 HI1 are not in the framing expected by IMP2’s Host Interface path (1822-oriented framing), despite UDP connectivity being present.

---

## 2) What Is Already Working

### Topology and process health
- `arpanet-vax`, `arpanet-imp1`, `arpanet-imp2`, `arpanet-pdp10` all up in Phase 2.
- `arpanet/scripts/test-phase2-imp-link.sh` reaches completion with Phase 2 markers.

### IMP-to-IMP path
- IMP1/IMP2 MI1 logs show sustained bidirectional packet flow and incrementing sequence numbers.
- This confirms modem-link/routing substrate is active.

### PDP-10 runtime
- PDP-10 is no longer failing with prior RP/CPU parse issues.
- It reaches ITS boot output and `DSKDMP` while container remains up.

---

## 3) Key Evidence for Current Blocker

### A. IMP2 sees malformed HI1 input from PDP-10 side
Observed repeatedly in IMP2 logs:

```text
HI1 UDP: link 1 - received packet w/bad magic number (magic=feffffff)
HI1 UDP: link 1 - received packet w/bad magic number (magic=00000219)
HI1 UDP: link 1 - received packet w/bad magic number (magic=ffffffff)
```

### B. PDP-10 KS-10 IMP device behavior is Ethernet/IP-oriented
`pdp10-ks` help output confirms IMP is configured like a network interface with:
- DHCP/NODHCP
- ARP table controls
- IP/GW/HOST settings
- `UNI` vs `SIMP` transfer modes

This behavior aligns with packetized IP/Ethernet semantics rather than direct IMP HI1 1822 framing expectations.

### C. Explicit runtime tuning tested
PDP-10 config currently includes:

```ini
set imp enabled
set imp simp
set imp ip=172.20.0.40/16
set imp gw=172.20.0.1
set imp host=172.20.0.40
set imp nodhcp
set imp debug
attach imp udp:2000:172.20.0.30:2000
```

Result:
- DHCP spam reduced/controlled (`IMP DHCP disabled` observed)
- Attach succeeds (`Eth: opened OS device udp:2000:172.20.0.30:2000`)
- But HI1 bad-magic on IMP2 persists.

---

## 4) Most Likely Root Cause

**Protocol boundary mismatch at IMP2 HI1 ingress**:

- IMP2 HI1 expects host packets in a specific ARPANET host-interface framing.
- PDP-10 KS-10 IMP device on this build appears to emit a different encapsulation format on UDP bridge path.
- Packets arrive, but fail magic/framing checks before higher-level host processing.

In short: **transport path exists; protocol contract does not match.**

---

## 5) Why This Blocks Host-to-Host Milestone

Until IMP2 can parse PDP-10 host-side packets correctly:
- No valid host-level traffic exchange across HI1.
- No meaningful VAX↔PDP-10 end-to-end probe beyond infra-level checks.
- FTP/transfer milestone remains blocked regardless of VAX application readiness.

---

## 6) Research Questions for a Problem-Solving LLM

1. For this KS-10 build (`git commit id: 627e6a6b`), what exact on-wire framing does `ATTACH IMP udp:...` emit in `UNI` vs `SIMP`?
2. What framing does H316 IMP `HI1` parser require on UDP link in this config lineage?
3. Is there a documented compatibility mode in either endpoint to bridge this mismatch directly?
4. If not, what is the thinnest adapter strategy:
   - packet translator sidecar (between PDP-10 and IMP2), or
   - alternate attach path/device mode on PDP-10, or
   - IMP2-side parser/config mode change?
5. Which approach minimizes regression risk to existing MI1 stability?

---

## 7) Recommended Next Experiments (Ordered)

1. **Capture and decode first bytes** of PDP-10→IMP2 UDP payloads on port 2000 to map observed magic fields.
2. **A/B test `set imp uni` vs `set imp simp`** with identical static IP settings, comparing IMP2 HI1 parse outcome.
3. **Pinpoint expected HI1 header format** from H316 code/docs and construct a packet-level compatibility matrix.
4. If mismatch is fundamental, **prototype a tiny UDP translator** that rewrites headers only and validate with IMP2 logs.
5. Re-run first host probe (VAX→PDP10 path) after framing compatibility is achieved.

---

## 8) Acceptance Criteria to Clear This Blocker

Blocker considered resolved only when all are true:

1. IMP2 no longer emits HI1 bad-magic errors for PDP-10 path.
2. IMP2 logs show valid HI1 receive/processing events from PDP-10 endpoint.
3. First host-level probe succeeds (beyond infra marker checks).
4. VAX↔PDP-10 transfer test reaches first successful payload round-trip.

---

## 9) Relevant Files

- `arpanet/configs/phase2/pdp10.ini` (current IMP settings under test)
- `arpanet/topology/generators.py` (source-of-truth for generated PDP-10 config)
- `tests/test_topology_generators.py` (assertions around generated PDP-10 config)
- `arpanet/scripts/test-phase2-imp-link.sh` (infrastructure validation script)
- `arpanet/Dockerfile.pdp10-its` (runtime image and KS-10 provenance)
