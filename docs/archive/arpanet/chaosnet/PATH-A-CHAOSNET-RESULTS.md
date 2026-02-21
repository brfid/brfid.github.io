# Path A Results: Chaosnet-First ITS-Compatible Path

> **⚠️ ARCHIVED**: 2026-02-11 - Blocked on ITS build, superseded by Serial Tunnel
> See: `docs/arpanet/archive/chaosnet/README.md`

**Date**: 2026-02-11
**Status**: Protocol Implementation Verified ✅ | Endpoint Blocked ❌
**Branch**: B (Path A)
**AWS Test Instance**: ~~`ubuntu@34.227.223.186`~~ Terminated 2026-02-11

---

## Summary

Path A Chaosnet implementation is complete. The protocol has been verified with the correct 12-byte header format. All local and AWS packet format tests pass. The infrastructure is ready for ITS integration testing once PDP-10 endpoint is available.

## Protocol Fix (2026-02-11)

**Critical Correction**: Header format changed from 10 bytes to 12 bytes.

| Field | Type | Bytes |
|-------|------|-------|
| pkt_type | unsigned short | 2 |
| length | unsigned short | 2 |
| src_host | unsigned short | 2 |
| src_subnet | unsigned short | 2 |
| dst_host | unsigned short | 2 |
| dst_subnet | unsigned short | 2 |
| **Total** | | **12** |

Format string: `>HHHHHH` (6 unsigned shorts, big-endian)

## Evidence of Progress

### Local Test Results

```bash
$ .venv/bin/python arpanet/scripts/test_chaosnet_transfer.py

2026-02-11 20:08:26,642 INFO: ============================================================
2026-02-11 20:08:26,642 INFO: Chaosnet Transfer Test Suite
2026-02-11 20:08:26,642 INFO: ============================================================
2026-02-11 20:08:26,068 INFO: --- Running: packet_format ---
2026-02-11 20:08:26,068 INFO: Packet format tests passed
2026-02-11 20:08:26,068 INFO: ✓ packet_format: PASSED (0.00s)
```

### AWS Test Results ✅

```bash
# Deployed to AWS and verified tests pass
$ ssh ubuntu@34.227.223.186
$ cd brfid.github.io
$ docker-compose -f docker-compose.arpanet.phase2-chaosnet.yml up -d --force-recreate
$ .venv/bin/python arpanet/scripts/test_chaosnet_transfer.py

2026-02-11 01:09:17,047 INFO: ============================================================
2026-02-11 01:09:17,047 INFO: Chaosnet Transfer Test Suite
2026-02-11 01:09:17,047 INFO: ============================================================
2026-02-11 01:09:17,047 INFO: --- Running: packet_format ---
2026-02-11 01:09:17,047 INFO: Packet format tests passed
2026-02-11 01:09:17,047 INFO: ✓ packet_format: PASSED (0.00s)
```

### Shim Logs (AWS)

```
2026-02-11 01:09:15,406 INFO chaosnet-shim: Starting Chaosnet shim on port 173
2026-02-11 01:09:15,407 INFO chaosnet-shim: PDP-10 target: host=0x7700, subnet=0x01
2026-02-11 01:09:15,407 INFO chaosnet-shim: ARPANET gateway: 172.20.0.30
2026-02-11 01:09:15,407 INFO chaosnet-shim: Chaosnet shim listening on port 173
2026-02-11 01:09:15,407 INFO chaosnet-shim: Entering main event loop
```

### Topology Tests (Local)

```bash
$ .venv/bin/python -m pytest tests/test_topology*.py -q
47 passed in 0.12s
```

---

## Completed Artifacts

### Files Created

| File | Status | Notes |
|------|--------|-------|
| `arpanet/scripts/chaosnet_shim.py` | ✅ Done | Protocol bridge with RFC/OPN/DAT/ACK handling |
| `arpanet/Dockerfile.chaosnet-shim` | ✅ Done | Python-based Chaosnet shim container |
| `arpanet/scripts/test_chaosnet_transfer.py` | ✅ Done | Test harness with packet validation |
| `arpanet/scripts/pdp10-chaosnet-enable.exp` | ✅ Done | Expect script for ITS Chaosnet config |
| `docs/arpanet/progress/PATH-A-CHAOSNET-PLAN.md` | ✅ Done | Implementation plan |

### Files Modified

| File | Changes |
|------|---------|
| `arpanet/topology/definitions.py` | Added `PHASE2_CHAOSNET_TOPOLOGY` with chaosnet-shim |
| `arpanet/topology/registry.py` | Added `chaosnet` to network_type Literal |
| `arpanet/scripts/chaosnet_shim.py` | Fixed header: `>HHHHHH` (12 bytes) |
| `arpanet/scripts/test_chaosnet_transfer.py` | Same fix, added `--shim-host`/`--shim-port` args |

### Generated Files

| File | Source |
|------|--------|
| `docker-compose.arpanet.phase2-chaosnet.yml` | `arpanet.topology.cli phase2-chaosnet` |
| `arpanet/configs/phase2-chaosnet/imp1.ini` | Generated |
| `arpanet/configs/phase2-chaosnet/imp2.ini` | Generated |
| `arpanet/configs/phase2-chaosnet/pdp10.ini` | Generated |

---

## Configuration

### Chaosnet Shim

- **Port**: 173 (octal 0255)
- **Header Size**: 12 bytes (format: `>HHHHHH`)
- **PDP-10 Host**: 0x7700 (BBN#7700)
- **PDP-10 Subnet**: 0x01

### Topology (phase2-chaosnet)

```
VAX:          172.20.0.10  (ARPANET HI1)
IMP1:         172.20.0.20  (ARPANET MI1 <-> HI1)
IMP2:         172.20.0.30  (ARPANET MI1 <-> HI1)
Host-IMP-Shim: 172.20.0.50  (H316 framing adapter)
PDP-10/ITS:   172.20.0.40  (Chaosnet endpoint)
Chaosnet-Shim: 172.20.0.60  (Chaosnet bridge)
```

---

## Deployment (AWS)

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186
cd brfid.github.io

# Rebuild and restart chaosnet topology
docker-compose -f docker-compose.arpanet.phase2-chaosnet.yml build
docker-compose -f docker-compose.arpanet.phase2-chaosnet.yml up -d --force-recreate

# Verify shim is running
docker logs arpanet-chaosnet-shim
```

---

## Known Issues

- **Connectivity test**: UDP port mapping from Docker host requires `network_mode: host` for direct testing. The shim runs correctly inside containers on the Docker network.

---

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| Chaosnet shim builds without errors | ✅ Verified |
| Packet format tests pass (12-byte header) | ✅ Verified |
| Shim listening on UDP 173 | ✅ Verified |
| PDP-10 ITS responds to Chaosnet RFC | ⏳ Pending PDP-10 ready |
| File transfer completes end-to-end | ⏳ Pending ITS integration |
| HI1 dual-window gate remains green | ⏳ Pending full integration |

---

## References

- Plan: `docs/arpanet/progress/PATH-A-CHAOSNET-PLAN.md`
- Progress: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Next steps: `docs/arpanet/progress/NEXT-STEPS.md`
