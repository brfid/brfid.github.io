# VAX + PDP-10 Serial Tunnel Architecture

**Date**: 2026-02-11
**Status**: Ready to Implement
**Path**: Direct Serial Tunnel (FTP over network)
**Emulator**: KL10 (not KS10 - incompatibility confirmed)

## Overview

This document describes the serial tunnel connection between VAX/4.3BSD and PDP-10/TOPS-20 (KL10 emulator) for direct host-to-host file transfer.

**Key Change**: Using KL10 emulator instead of KS10 due to confirmed boot failures. Chaosnet deferred (too complex).

## Architecture Phases

### Current Architecture: Direct Network + Serial Tunnel

```
┌─────────────────┐                              ┌─────────────────┐
│  VAX/4.3BSD     │        Docker Network        │  PDP-10/TOPS-20 │
│  SIMH VAX       │◄────────────────────────────►│  SIMH KL10      │
│  172.20.0.10    │      172.20.0.0/16           │  172.20.0.40    │
│                 │                              │                 │
│  FTP Client     │      FTP (port 21)           │  FTP Server     │
│  Console: 2323  │                              │  Console: 2326  │
└─────────────────┘                              └─────────────────┘
        │                                                │
        │            Serial Tunnel (optional)            │
        │                                                │
        └──────────► socat (ports 9000/9001) ◄──────────┘
```

**Purpose**: Direct file transfer between VAX and PDP-10 using FTP over Docker network.

**Serial Tunnel**: Optional console bridge for debugging/monitoring, not required for file transfer.

**Key Points**:
- **Network**: Both on same Docker bridge (172.20.0.0/16)
- **Transfer**: FTP directly via network (not through serial)
- **Emulator**: KL10 (KS10 confirmed incompatible)
- **OS**: TOPS-20 V4.1 (ITS build timeout)

## File Inventory

### Docker Compose

| File | Purpose |
|------|---------|
| `docs/legacy/archived/docker-compose.vax-pdp10-serial.yml` | Phase 1: Serial tunnel (archived) |
| `docker-compose.vax-pdp10-chaosnet.yml` | Phase 2-3: Chaosnet |

### Scripts

| File | Purpose |
|------|---------|
| `arpanet/scripts/chaosnet_shim.py` | Chaosnet NCP protocol bridge |
| `arpanet/scripts/serial-tunnel.sh` | socat tunnel automation |

### Dockerfiles

| File | Purpose |
|------|---------|
| `vax/Dockerfile.simh-ftp` | VAX with FTP server (active) |
| `arpanet/Dockerfile.pdp10-kl10` | PDP-10 TOPS-20 with KL10 emulator |
| ~~`arpanet/Dockerfile.pdp10`~~ | ~~KS10 TOPS-20~~ (archived, boot failure) |
| ~~`arpanet/Dockerfile.pdp10-its`~~ | ~~KS10 ITS~~ (archived, boot failure) |

## Quick Start

### Prerequisites
1. Build KL10 container (see `docs/arpanet/progress/NEXT-STEPS.md`)
2. Install TOPS-20 on PDP-10 (interactive, ~2 hours)
3. Configure FTP server on both systems

### File Transfer (Primary Use Case)

```bash
# Start both containers
docker compose --project-directory . -f docs/legacy/archived/docker-compose.vax-pdp10-serial.yml up -d

# Test network connectivity
docker exec vax-host ping -c 3 172.20.0.40

# Transfer file VAX → PDP-10
docker exec -it vax-host telnet localhost 2323
# Login to VAX
$ ftp 172.20.0.40
ftp> put /tmp/file.txt file.txt
ftp> quit
```

### Serial Tunnel (Optional, for Debugging)

```bash
# On AWS host
~/serial-tunnel.sh

# Connect to VAX via tunnel
telnet localhost 9000

# Connect to PDP-10 via tunnel
telnet localhost 9001
```

## History

This approach was chosen after multiple iterations:
1. **IMP chain blocked**: HI1 framing mismatch (KS10 IMP device vs H316 IMP simulator)
2. **KS10 emulator blocked**: Both ITS and TOPS-20 fail with "Stop code 7, PC: 000100"
3. **Chaosnet deferred**: ITS build timeout, added complexity
4. **Direct network + KL10**: Simplest working path
   - KL10 proven by community (Gunkies recipe)
   - FTP directly over Docker network
   - No complex routing needed

## References

- **Master Plan**: `docs/arpanet/KL10-SERIAL-FTP-PLAN.md`
- **Next Steps**: `docs/arpanet/progress/NEXT-STEPS.md`
- **Archived**:
  - IMP topology: `arpanet/archived/README.md`
  - Chaosnet Path A: `docs/arpanet/archive/chaosnet/README.md`
  - KS10 boot failures: `docs/arpanet/archive/ks10/README.md`
