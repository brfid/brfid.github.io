# Path A Implementation Plan: Chaosnet-First ITS-Compatible Path

> **⚠️ ARCHIVED**: 2026-02-11 - Blocked on ITS build, superseded by Serial Tunnel
> See: `docs/arpanet/archive/chaosnet/README.md`

**Date**: 2026-02-10
**Status**: ~~Implementation In Progress~~ **ARCHIVED** (ITS build blocker)
**Branch**: B (Path A)
**AWS Testing**: ~~Active at `ubuntu@34.227.223.186`~~ Terminated 2026-02-11

---

## Overview

Implement a Chaosnet-first approach for host-to-host file transfer between VAX/BSD and PDP-10/ITS, bypassing the TCP/IP networking limitation in the current KS10 runtime profile. This path leverages ITS's native Chaosnet support (NCP protocol) instead of requiring full TCP/IP stack support on the PDP-10.

The core insight from upstream ITS documentation is that "The SIMH KS10 does not have the necessary support" for full TCP/IP networking. Chaosnet was ITS's primary networking protocol before TCP/IP integration and is fully supported in the ITS runtime.

---

## Types

### Topology Components

```yaml
VAX:
  ip: "172.20.0.10"
  role: "Build artifact source"
  network: "ARPANET (HI1)"

IMP1:
  ip: "172.20.0.20"
  role: "ARPANET router"
  interface: "HI1 (VAX), MI1 (IMP2)"

IMP2:
  ip: "172.20.0.30"
  role: "ARPANET router"
  interface: "MI1 (IMP1), HI1 (Host-IMP)"

Host-IMP-Shim:
  ip: "172.20.0.50"
  role: "Protocol adapter (H316 framing)"
  ports:
    - "2000"  # IMP2 HI1 ingress
    - "2001"  # PDP-10 IMP egress

PDP-10-ITS:
  ip: "172.20.0.40"
  role: "Chaosnet endpoint"
  chaosnet_host: "BBN#7700"  # Typical ITS Chaosnet address
  network: "Chaosnet (NCP)"
```

### Chaosnet Protocol Requirements

```yaml
Chaosnet:
  protocol: "NCP (Network Control Program)"
  port: "Octal 0255 (173 decimal)"  # Standard Chaosnet listen port
  packet_types:
    - "RFC"  # Request for Connection
    - "OPN"  # Open Connection
    - "CLS"  # Close Connection
    - "DAT"  # Data
    - "ACK"  # Acknowledgment
    - "FWD"  # Forward (routing)
  addressing:
    host: "8-bit host number"
    subnet: "8-bit subnet number"
```

---

## Files

### New Files to Create

| File | Purpose |
|------|---------|
| `arpanet/scripts/chaosnet_shim.py` | Chaosnet-to-ARPANET protocol bridge |
| `arpanet/Dockerfile.chaosnet-shim` | Container for Chaosnet bridge service |
| `arpanet/scripts/test_chaosnet_transfer.py` | Validation script for Chaosnet transfer |
| `docs/arpanet/progress/PATH-A-CHAOSNET-RESULTS.md` | Execution results and evidence |

### Existing Files to Modify

| File | Changes |
|------|---------|
| `docker-compose.arpanet.phase2.yml` | Add chaosnet-shim service |
| `arpanet/topology/definitions.py` | Add chaosnet topology definitions |
| `arpanet/topology/generators.py` | Generate chaosnet-shim configs |
| `docs/arpanet/progress/NEXT-STEPS.md` | Update with Path A commands |
| `docs/arpanet/INDEX.md` | Add Path A plan reference |

### Configuration Files to Create

| File | Purpose |
|------|---------|
| `arpanet/configs/chaosnet-shim.ini` | SIMH config for chaosnet bridge |
| `arpanet/configs/phase2/chaosnet.ini` | Phase 2 topology config |

---

## Functions

### New Functions

#### chaosnet_shim.py

```python
def wrap_chaosnet_packet(data: bytes, dest_host: int, dest_subnet: int) -> bytes
    """Wrap data in Chaosnet NCP packet format."""

def unwrap_chaosnet_packet(data: bytes) -> tuple[bytes, int, int]
    """Extract data and addressing from Chaosnet packet."""

def handle_rfc(src_host: int, src_subnet: int, data: bytes) -> bytes
    """Handle RFC (Request for Connection) packets."""

def handle_dat(data: bytes) -> bytes
    """Handle DAT (Data) packets for file transfer."""
```

#### test_chaosnet_transfer.py

```python
def verify_chaosnet_connectivity() -> bool
    """Verify PDP-10 responds to Chaosnet RFC."""

def transfer_file_via_chaosnet(src_path: str, dest_path: str) -> bool
    """Execute file transfer using Chaosnet protocol."""

def capture_chaosnet_evidence() -> dict
    """Capture evidence artifacts for the transfer."""
```

### Modified Functions

| Function | File | Change |
|----------|------|--------|
| `run_hi1_gate_remote.py` | `test_infra/scripts/` | Add chaosnet-shim validation to dual-window gate |

---

## Classes

### New Classes

#### ChaosnetShim (arpanet/scripts/chaosnet_shim.py)

```python
class ChaosnetShim:
    """Chaosnet-to-ARPANET protocol adapter."""
    
    def __init__(self, config: dict):
        self.pdp10_host = config['pdp10_host']  # e.g., 0x7700
        self.pdp10_subnet = config['pdp10_subnet']  # e.g., 0x01
        self.listen_port = 173  # Octal 0255
        self.arpabet_gateway = "172.20.0.30"  # IMP2
        
    def start(self) -> None:
        """Start the Chaosnet shim service."""
        
    def process_packet(self, packet: bytes) -> bytes:
        """Process incoming packet and return response."""
```

#### ChaosnetTransferValidator (arpanet/scripts/test_chaosnet_transfer.py)

```python
class ChaosnetTransferValidator:
    """Validates Chaosnet file transfer capability."""
    
    def __init__(self, topology: dict):
        self.topology = topology
        
    def pre_transfer_check(self) -> dict:
        """Verify all components are ready."""
        
    def execute_transfer(self, artifact: str) -> dict:
        """Execute the file transfer."""
        
    def post_transfer_verification(self) -> bool:
        """Verify transfer succeeded."""
```

---

## Dependencies

### New Python Packages

```txt
# No new packages required - using standard library
# Existing: docker, subprocess, json, dataclasses
```

### Docker Images

```yaml
chaosnet-shim:
  base: "python:3.11-slim"
  purpose: "Chaosnet protocol adapter"
  ports:
    - "173:173"  # Chaosnet listen port
```

### External Resources

- ITS Chaosnet documentation: `PDP-10/its` repository `doc/networking.md`
- Chaosnet protocol specification: RFC 673 (historical reference)

---

## Testing

### Test Files to Create

| Test File | Coverage |
|-----------|----------|
| `tests/test_chaosnet_shim.py` | Unit tests for packet wrapping/unwrapping |
| `tests/test_chaosnet_transfer.py` | Integration tests for transfer workflow |

### Test Scenarios

1. **Unit Tests** (local, no Docker)
   - Packet format validation
   - Host/subnet addressing
   - RFC/OPN/DAT packet handling

2. **Integration Tests** (requires AWS)
   - Chaosnet connectivity check
   - File transfer execution
   - Evidence capture

3. **Regression Tests**
   - HI1 dual-window gate still passes
   - No bad-magic introduced by chaosnet-shim

### Validation Commands

```bash
# Pre-transfer validation
.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py \
  --dual-window \
  --manifest-output build/arpanet/analysis/chaosnet-pre-validate.json

# Chaosnet transfer test
.venv/bin/python arpanet/scripts/test_chaosnet_transfer.py \
  --artifact /tmp/test-file.txt \
  --output build/arpanet/analysis/chaosnet-transfer-result.json

# Post-transfer regression check
.venv/bin/python test_infra/scripts/run_hi1_gate_remote.py \
  --dual-window \
  --manifest-output build/arpanet/analysis/chaosnet-post-transfer.json
```

---

## Implementation Order

### Phase A1: Chaosnet Shim Foundation (Day 1) ✅ COMPLETED

1. [x] Create `arpanet/scripts/chaosnet_shim.py` with basic packet handling
2. [x] Create `arpanet/Dockerfile.chaosnet-shim`
3. [x] Add chaosnet topology definitions to `arpanet/topology/definitions.py`
4. [x] Update `arpanet/topology/generators.py` for chaosnet-shim config generation
5. [x] Update `docker-compose.arpanet.phase2.yml` with chaosnet-shim service

### Phase A2: PDP-10 Chaosnet Configuration (Day 2) ✅ COMPLETED

6. [x] Research exact ITS Chaosnet commands for file transfer
7. [x] Create ITS-side Chaosnet enablement script (`pdp10-chaosnet-enable.exp`)
8. [x] Configure PDP-10 ITS for Chaosnet host number (BBN#7700)
9. [ ] Verify PDP-10 responds to Chaosnet RFC (requires AWS deployment)

### Phase A3: Transfer Implementation (Day 3) ✅ COMPLETED (unit tests)

10. [x] Implement `arpanet/scripts/test_chaosnet_transfer.py`
11. [x] Create test artifact file
12. [ ] Execute first Chaosnet file transfer (requires AWS deployment)
13. [ ] Capture evidence artifacts (requires AWS deployment)

### Phase A4: Validation and Documentation (Day 4)

14. [ ] Run full regression suite (HI1 dual-window gate)
15. [ ] Document results in `docs/arpanet/progress/PATH-A-CHAOSNET-RESULTS.md`
16. [ ] Update `docs/arpanet/progress/NEXT-STEPS.md` with Path A status
17. [ ] Commit artifacts and update central progress

---

## Acceptance Criteria

### Must Have (for Path A Success)

- [ ] Chaosnet shim builds and runs without errors
- [ ] PDP-10 ITS responds to Chaosnet RFC packets
- [ ] File transfer completes end-to-end via Chaosnet
- [ ] Post-transfer HI1 dual-window gate remains green:
  - `final_exit=0`
  - `bad_magic_total_delta=0`
- [ ] Evidence artifacts captured in `build/arpanet/analysis/`

### Nice to Have

- [ ] Automated transfer script (no manual steps)
- [ ] Checksum verification of transferred file
- [ ] Multiple file transfer tests

---

## AWS Access

```bash
# Connect to AWS test instance
ssh -i ~/.ssh/id_ed25519 ubuntu@34.227.223.186

# Workspace
cd brfid.github.io

# Quick status check
docker compose -f docker-compose.arpanet.phase2.yml ps
```

---

## References

- Previous blocker analysis: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- FTP blocker handoff: `docs/arpanet/handoffs/LLM-PDP10-FTP-BLOCKER-2026-02-10.md`
- Current progress: `docs/arpanet/progress/PHASE3-PROGRESS.md`
- Next steps: `docs/arpanet/progress/NEXT-STEPS.md`