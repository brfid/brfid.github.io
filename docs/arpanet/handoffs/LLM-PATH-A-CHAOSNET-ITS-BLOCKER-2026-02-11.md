# Path A Chaosnet ITS Blocker Analysis

**Date**: 2026-02-11  
**Purpose**: Document the ITS disk build blocker for Path A (Chaosnet-first) and implications for host-imp-imp-host FTP

---

## Executive Summary

Path A (Chaosnet-first ITS-compatible path) is **blocked** at the infrastructure layer. The Chaosnet shim and routing infrastructure is fully operational, but the PDP-10 container is running TOPS-20 instead of ITS, preventing Chaosnet networking.

### Status Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| Chaosnet shim | ✅ Running | `python /app/chaosnet_shim.py --listen-port 173` |
| IMP2 routing | ✅ Configured | UDP 2000 → 172.20.0.60:173 |
| PDP-10 ITS disk | ❌ Missing | No `its.dsk` in data volume |
| Deployed image | TOPS-20 | Docker history shows `tops20_v41.tap` |

---

## Root Cause Analysis

### The Protocol Mismatch Problem

The SIMH `pdp10-ks` "IMP" device does **not** implement the ARPANET 1822 host interface. Instead, it behaves as an Ethernet/IP NIC:

```text
0x0030: ffff ffff ffff 0000 0219 9e8f 0806 0001
0x0040: 0800 0604 0001 0000 0219 9e8f ac14 0028
```

`0806` is Ethernet ARP EtherType - confirming Ethernet-family payloads where HI1 expects 1822 framing.

### Why This Matters for FTP

| Protocol Layer | Expected | Actual |
|---------------|----------|--------|
| ARPANET HI1 | 1822 host frames | Ethernet/IP NIC |
| PDP-10 IMP | Native IMP interface | SIMH `imp` device |
| FTP transport | TCP over 1822 | ARP/TCP/IP |

The `hi1_shim.py` wraps H316 envelopes to make IMP2 happy at the framing layer, but the inner payload semantics still don't match.

---

## What We Tried

### Attempt 1: Rebuild ITS Disk (Timestamp: Feb 11 02:43 UTC)

```bash
docker-compose -f docker-compose.arpanet.phase2-chaosnet.yml build --no-cache pdp10
```

**Outcome**: Build timed out at ~400 seconds (before disk image creation)

**Last log before timeout**:
```
DB ITS 1652 IN OPERATION AT
NETWRK 266 included in this assembly.
```

### Attempt 2: Rebuild with 1-hour timeout (Timestamp: Feb 11 03:02 UTC)

```bash
timeout 3600 docker-compose build --no-cache pdp10
```

**Outcome**: Build progressed to ~1800 seconds but didn't complete before SSH connection dropped

**Last observed state**:
- ITS booted successfully
- Build running WHO% and DECSYS compilation
- No final disk image created

---

## What Needs to Happen for Path A to Work

### Prerequisite: Complete ITS Build

The Docker build must:
1. Complete ITS compilation (all build scripts)
2. Copy `its.dsk` to `/opt/its-seed/its.dsk`
3. Dockerfile must copy disk to persistent volume at `/machines/data/its.dsk`

### Required Files

```
/opt/its-seed/its.dsk          # Seed disk from build
/machines/data/its.dsk         # Runtime disk (persist across restarts)
/machines/pdp10.ini            # SIMH config pointing to correct disk
```

### Current Docker State

```bash
# The deployed image is TOPS-20
$ docker history brfidgithubio-pdp10 | grep -i tape
COPY /tmp/tops20/tops20_v41.tap /machines/pdp10/tops20_v41.tap

# Data volume has empty/disk missing
$ sudo ls -la /var/lib/docker/volumes/brfid.github.io_arpanet-pdp10-data/_data/
total 8
drwxr-xr--- 2 root root 4096 Feb 8 22:25 .
drwxr-xr-x 3 root root 4096 Feb 8 21:55 ..
-rw-r--r-- 1 root root    0 Feb 8 22:25 tops20.dsk  # 0 bytes!
```

---

## Infrastructure That's Ready

### Chaosnet Shim (`arpanet/scripts/chaosnet_shim.py`)

```
Listening: UDP port 173
PDP-10 target: host=0x7700, subnet=0x01
ARPANET gateway: 172.20.0.30 (IMP2)
```

Protocol implementation verified with 12-byte header format (`>HHHHHH`):
- pkt_type (2 bytes)
- length (2 bytes)
- src_host (2 bytes)
- src_subnet (2 bytes)
- dst_host (2 bytes)
- dst_subnet (2 bytes)

### Topology (docker-compose.arpanet.phase2-chaosnet.yml)

```
VAX:          172.20.0.10  (ARPANET HI1)
IMP1:         172.20.0.20  (ARPANET MI1 <-> HI1)
IMP2:         172.20.0.30  (ARPANET MI1 <-> HI1)
Host-IMP-Shim: 172.20.0.50  (H316 framing adapter)
PDP-10/ITS:   172.20.0.40  (Chaosnet endpoint)
Chaosnet-Shim: 172.20.0.60  (Chaosnet bridge)
```

### Enablement Script (`arpanet/scripts/pdp10-chaosnet-enable.exp`)

Ready to configure ITS Chaosnet:
- Connects to PDP-10 console (telnet 172.20.0.40:2326)
- Sets Chaosnet host to 7700, subnet to 01
- Enables NCP (Network Control Program)
- Starts listener on port 173

---

## Alternative Paths

### Path D: VAX/IMP Transfer Proof

Keep proven ARPANET routing, prove transfer with an endpoint that speaks 1822:
- Requires finding PDP-10 image with native TCP/IP OR 1822 host interface
- SIMH KA10 or other emulator with different networking

### Direct IP Path (Bypasses ARPANET)

If TOPS-20 has FTP server running:
```bash
# From VAX:
ftp 172.20.0.40
```

This would bypass ARPANET routing entirely.

---

## Commands for Next Operator

### Retry ITS Build (Recommended)

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186
cd brfid.github.io

# Full rebuild with extended timeout
docker-compose -f docker-compose.arpanet.phase2-chaosnet.yml build --no-cache pdp10

# Monitor output
tail -f /tmp/its-rebuild.log

# If it completes successfully:
docker-compose up -d

# Verify ITS is running
docker logs arpanet-pdp10 --tail 50
```

### Verify Chaosnet Shim

```bash
# Check shim is listening
docker logs arpanet-chaosnet-shim --tail 20

# Should show:
# "Chaosnet shim listening on port 173"
# "PDP-10 target: host=0x7700, subnet=0x01"
```

### Test Connectivity

```bash
# From VAX to PDP-10
docker exec arpanet-vax ping -c 3 172.20.0.40

# From PDP-10 console
docker exec -it arpanet-pdp10 telnet localhost 2326
# Should see ITS prompt if running
```

---

## References

- Path A plan: `docs/arpanet/progress/PATH-A-CHAOSNET-PLAN.md`
- Path A results: `docs/arpanet/progress/PATH-A-CHAOSNET-RESULTS.md`
- KS10 IMP mismatch: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- Next steps: `docs/arpanet/progress/NEXT-STEPS.md`
- Chaosnet shim: `arpanet/scripts/chaosnet_shim.py`
- PDP-10 enablement: `arpanet/scripts/pdp10-chaosnet-enable.exp`

---

## Key Insight for Future Research

The fundamental issue is **protocol compatibility at the host-IMP boundary**:

1. **SIMH KS10 IMP device**: Ethernet/IP NIC semantics (modern interpretation)
2. **ARPANET 1822**: Historical host interface with different framing
3. **HI1 shim**: Translates outer framing but doesn't fix inner semantics
4. **ITS Chaosnet**: Native Chaosnet protocol (different from 1822)

For authentic ARPANET FTP, you need:
- A PDP-10 image that implements 1822 host interface, OR
- Protocol translation at the boundary (like Chaosnet shim), OR
- Native TCP/IP on the PDP-10 (TOPS-20 or modern ITS with TCP)

The Chaosnet shim approach (Path A) is the most historically authentic for ITS, but requires the ITS disk to be properly built and deployed.
