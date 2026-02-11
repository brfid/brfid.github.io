# VAX + PDP-10 Serial Tunnel Architecture

**Date**: 2026-02-11
**Status**: In Progress
**Path**: Serial-over-TCP → Chaosnet-on-Serial → Full Chaosnet Bridge

## Overview

This document describes the iterative approach to connecting VAX/4.3BSD and PDP-10/ITS (or TENEX) via a serial tunnel, with optional upgrades to Chaosnet.

## Architecture Phases

### Phase 1: Serial-over-TCP Tunnel (Fastest validation)

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  VAX/4.3BSD     │  TCP    │  Serial-TCP    │  TCP    │  PDP-10/ITS     │
│  SIMH DZ11      │◄───────►│  Tunnel        │◄───────►│  SIMH DL11      │
│  :2323 (console)│  :9000  │  (socat)       │  :9001  │  :2326 (console)│
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

**Purpose**: Validate basic connectivity between VAX and PDP-10.

**Implementation**:
- `socat TCP-LISTEN:9000,fork TCP:localhost:2323` (VAX redirect)
- `socat TCP-LISTEN:9001,fork TCP:localhost:2326` (PDP-10 redirect)
- Cross-connect for true tunnel: `socat TCP:localhost:9000 TCP:localhost:9001`

**Test**:
```bash
# From PDP-10 side
telnet localhost 9000  # Should connect to VAX console
```

### Phase 2: Chaosnet-on-Serial (Interesting upgrade)

```
┌─────────────────┐    Serial    ┌─────────────────┐    Serial    ┌─────────────────┐
│  VAX/4.3BSD     │◄───────────►│  Chaosnet-Shim │◄───────────►│  PDP-10/ITS     │
│  Chaosnet Client │   :173      │  (serial)       │   :173      │  Native Chaosnet│
└─────────────────┘              └─────────────────┘              └─────────────────┘
```

**Purpose**: Implement Chaosnet protocol on both ends using serial as transport.

**Implementation**:
- Shim translates serial ↔ Chaosnet NCP
- VAX runs simple Chaosnet client
- PDP-10 uses native ITS Chaosnet (if available) or simulated

### Phase 3: Full Chaosnet Bridge (Ultimate goal)

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│  VAX/4.3BSD     │  TCP    │  Chaosnet-TCP   │  TCP    │  PDP-10/ITS     │
│  Chaosnet Client │◄───────►│  Gateway        │◄───────►│  Native Chaosnet│
│                 │  :1917   │  (chaosnet_shim)│  :1917  │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

**Purpose**: TCP encapsulation of Chaosnet for cross-network connectivity.

## File Inventory

### Docker Compose

| File | Purpose |
|------|---------|
| `docker-compose.vax-pdp10-serial.yml` | Phase 1: Serial tunnel |
| `docker-compose.vax-pdp10-chaosnet.yml` | Phase 2-3: Chaosnet |

### Scripts

| File | Purpose |
|------|---------|
| `arpanet/scripts/chaosnet_shim.py` | Chaosnet NCP protocol bridge |
| `arpanet/scripts/serial-tunnel.sh` | socat tunnel automation |

### Dockerfiles

| File | Purpose |
|------|---------|
| `vax/Dockerfile.simh-ftp` | VAX with FTP server (fallback) |
| `arpanet/Dockerfile.pdp10` | PDP-10 TOPS-20 |
| `arpanet/Dockerfile.pdp10-its` | PDP-10 ITS (preferred) |

## Quick Start (Phase 1)

```bash
# Start VAX and PDP-10
docker-compose -f docker-compose.vax-pdp10-serial.yml up -d

# Set up serial tunnel
docker exec vax-host socat TCP-LISTEN:9000,fork TCP:localhost:2323 &
docker exec pdp10-host socat TCP-LISTEN:9001,fork TCP:localhost:2326 &

# Cross-connect for tunnel
docker exec vax-host socat TCP:localhost:9000 TCP:localhost:9001 &

# Test from PDP-10 to VAX
telnet localhost 9000
```

## History

This approach was chosen because:
1. The IMP chain was blocked on HI1 framing mismatch (KS10 vs H316)
2. PDP-10 ITS bootstrap failed on SIMH KS10
3. Serial tunnel is the simplest possible connection - minutes to validate
4. Once serial works, Chaosnet can be layered on top
5. No IMPs needed - direct VAX-to-PDP-10 connection

## References

- Archived IMP topology: `arpanet/archived/README.md`
- KS10 blocker: `docs/arpanet/handoffs/LLM-KS10-IMP-MISMATCH-2026-02-10.md`
- Chaosnet protocol: `arpanet/scripts/chaosnet_shim.py`
