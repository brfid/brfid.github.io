# Panda TOPS-20 Approach - TCP/IP Direct Path

**Date**: 2026-02-12
**Status**: In progress (BOOT handoff not yet proven to `@`)
**Goal**: VAX → PDP-10 file transfer using TCP/IP (bypassing ARPANET 1822)

> **Current-truth note**: This document explains architecture and intent. For live pass/fail status, use `CHANGELOG.md` and `docs/arpanet/progress/NEXT-STEPS.md`.

---

## Why This Approach?

### Previous Blockers
All previous PDP-10 attempts failed due to:
1. **TOPS-20 V4.1**: Boot loop bug (WRCSTM instruction)
2. **TOPS-20 V7.0**: Cornwell SIMH parameter incompatibilities
3. **KLH10**: Docker execution errors with standard images
4. **Protocol Mismatch**: VAX Ethernet/IP ↔ ARPANET 1822 incompatibility

### Panda Distribution Direction
The Panda TOPS-20 distribution addresses several major blockers, but does **not** yet complete end-to-end bring-up in this repo:
- ✅ **Pre-built disk image** (`RH20.RP07.1`) available in Panda distribution
- ✅ **KLH10 emulator** runs in Docker for current build path
- ✅ **TCP/IP networking model** via `dpni20` (direct IP path, no 1822 host bridge)
- ⚠️ **Remaining blocker**: BOOT control-plane ingress is unstable; strict automation has not yet proven a real TOPS-20 `@` prompt

---

## Architecture

```
┌─────────────────┐                    ┌─────────────────┐
│   VAX/BSD 4.3   │                    │ PDP-10/TOPS-20  │
│                 │                    │  (Panda dist)   │
│  172.20.0.10    │◄──────TCP/IP──────►│  172.20.0.40    │
│                 │                    │                 │
│  de0 (Ethernet) │                    │  ni0 (dpni20)   │
│  FTP client     │                    │  FTP server     │
└─────────────────┘                    └─────────────────┘
         │                                      │
         └──────────────────┬───────────────────┘
                            │
                   Docker Bridge Network
                      172.20.0.0/16
```

**Key Difference**: Both systems use TCP/IP directly on the Docker network.
No ARPANET 1822 protocol, no IMPs, no protocol translation needed.

---

## Implementation

### Files Created
- `arpanet/Dockerfile.pdp10-panda` - KLH10 + Panda distribution build
- `arpanet/configs/panda.ini` - KLH10 runtime configuration
- `docker-compose.panda-vax.yml` - Simplified VAX + PDP-10 setup
- `arpanet/scripts/test_panda_vax.py` - Automated connectivity tests

### Build Process
```bash
# Download Panda distribution (~221MB)
wget http://panda.trailing-edge.com/panda-dist.tar.gz

# Build KLH10 emulator from source
cd panda-dist/klh10-2.0h/bld-linux
make

# Use pre-built disk image
cp RH20.RP07.1 /opt/tops20/
```

### Network Configuration
**PDP-10 (KLH10 config)**:
```ini
devdef ni0 0 ni dpni:172.20.0.40
```
- Uses `dpni20` driver for TCP/IP
- Requires privileged mode in Docker
- Direct IP assignment (no DHCP)

**VAX (BSD 4.3)**:
```bash
/etc/ifconfig de0 172.20.0.10 netmask ffff0000 up
```
- Standard Ethernet interface
- TCP/IP stack already configured

---

## Usage

### Starting the System
```bash
# Build containers
docker compose -f docker-compose.panda-vax.yml build

# Start both systems
docker compose -f docker-compose.panda-vax.yml up -d
```

Then validate runtime status and console behavior:

```bash
docker compose -f docker-compose.panda-vax.yml ps
docker logs panda-pdp10 --tail 100
```

### Accessing Systems
```bash
# VAX console (BSD 4.3)
telnet localhost 2323

# PDP-10 console (TOPS-20) - preferred path
docker attach panda-pdp10

# PDP-10 console fallback
telnet localhost 2326
```

> Note: host-mapped `localhost:2326` may connect then close in some runs. Prefer `docker attach panda-pdp10` for BOOT handoff debugging.

### TOPS-20 Commands
```
BOOT> /G143

# fallback sequence
BOOT> /E
dbugsw/ 2
147$G

@log operator dec-20
@enable
@ipservice          ; Start FTP/Telnet services
@information services  ; Check running services
```

### Testing FTP Transfer
**From VAX**:
```bash
# Connect to PDP-10
ftp 172.20.0.40

# Login (operator/operator or operator/blank)
Name: operator
Password:

# Transfer test file
put bradman.c
quit
```

**From PDP-10**:
```
@directory          ; List files
@type bradman.c     ; View transferred file
```

---

## Advantages Over Previous Approaches (Architectural)

| Aspect | Previous (ARPANET 1822) | Panda (TCP/IP) |
|--------|-------------------------|----------------|
| **Installation** | Manual or automation (failed) | Pre-built disk image |
| **Emulator** | SIMH (boot bugs) | KLH10 (stable) |
| **Protocol** | VAX Ethernet ↔ 1822 mismatch | Both use TCP/IP |
| **Complexity** | Gateway needed (weeks) | Direct connection path is simpler |
| **Boot Reliability** | Multiple prior blockers | BOOT prompt reached; login proof still pending |
| **Network Setup** | Protocol translation | Standard Docker networking |

---

## Trade-offs

### What We Gain
- ✅ Clear path to VAX ↔ PDP-10 TCP/IP transfer once BOOT handoff is stable
- ✅ Authentic vintage systems (VAX/BSD 4.3, TOPS-20)
- ✅ Real TCP/IP networking (1980s-era)
- ✅ Lower protocol complexity versus 1822 host bridge

### What We Lose
- ❌ ARPANET 1822 protocol demonstration
- ❌ IMP routing visualization
- ❌ Historical packet-switching network

### Hybrid Option
Keep BOTH approaches:
1. **Panda path**: For working file transfer demo
2. **IMP routing**: For ARPANET protocol showcase (IMP-to-IMP already works)

Resume narrative:
> "Implemented vintage computing pipeline with VAX/BSD 4.3 and PDP-10/TOPS-20,
> featuring both modern containerization and historical ARPANET protocol simulation
> (IMP-to-IMP routing). File transfer achieved via 1980s-era TCP/IP stack."

---

## Success Criteria

### Minimum Viable Demo
- [x] Build Panda container
- [ ] Complete BOOT handoff to real TOPS-20 `@` prompt (hard proof)
- [ ] Establish network connectivity (ping)
- [ ] FTP connection from VAX
- [ ] Transfer compiled C binary
- [ ] Verify file on PDP-10

### Stretch Goals
- [ ] Automated file transfer script
- [ ] Integration with resume generation pipeline
- [ ] Logging/monitoring of transfers
- [ ] Performance metrics

---

## References

- **Panda Distribution**: http://panda.trailing-edge.com/
- **KLH10 Documentation**: Included in `panda-dist/doc/`
- **TOPS-20 User Guide**: `panda-dist/doc/tops20-user.txt`
- **dpni20 Driver**: Network interface driver for KLH10

---

## Next Steps

1. **Capture one known-good manual BOOT transcript**
   - Use `docker attach panda-pdp10`
   - Reach real `@` prompt via `/G143` or fallback sequence
   - Record timing and command sequence

2. **Codify that behavior in automation**
   - Update/validate `arpanet/scripts/panda_boot_handoff.py`
   - Run strict retries requiring `\n@` proof

3. **Only after `@` proof: validate services and transfer**
   - Configure TOPS-20 network files for `172.20.0.40`
   - Test VAX-side FTP to PDP-10
   - Capture evidence transcript/logs

4. **Keep IMP route as parallel historical signal**
   - IMP-to-IMP validation remains useful as separate ARPANET evidence
