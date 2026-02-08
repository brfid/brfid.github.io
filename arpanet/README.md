# ARPANET Build Integration

This directory contains the infrastructure for integrating ARPANET components into the build pipeline. The goal is to create a phased approach that slowly adds ARPANET components until there's an authentic 1970s network connection inside the build process.

## Overview

The integration is based on the [obsolescence/arpanet](https://github.com/obsolescence/arpanet) project, which recreates the ARPANET circa 1972-73 using SIMH emulation of period-accurate hardware.

## Architecture

### Phase 1: VAX + IMP (Complete)

```
[VAX/BSD] ←→ [IMP #1]
   |             |
  de0         Port 2000
   |             |
172.20.0.10  172.20.0.20
```

**Components:**
- **VAX/BSD**: Existing build container running 4.3BSD with DEC Ethernet (de0)
- **IMP #1**: Honeywell 316/516 simulator running original IMP firmware

**Purpose**: Establish basic connectivity between VAX and IMP, validate network interface configuration.

**Testing**: AWS EC2 x86_64 instances used for architecture-specific testing (see `test_infra/`)

### Phase 2: Multi-IMP Network (In Progress)

```
[VAX/BSD] ←→ [IMP-1] ←→ [IMP-2] ←→ [PDP-10/ITS]
```

**Purpose**: Create minimal but authentic ARPANET topology with file transfer capability between hosts.

**Current Phase 2 milestone**:
```
[VAX/BSD] ←→ [IMP-1] ←→ [IMP-2] ←→ [PDP10 host stub]
```

- IMP↔IMP modem link (MI1) validated on AWS EC2 x86_64
- Active packet exchange visible in both IMP debug logs
- IMP2 HI1 host-link is now attached to a PDP10 UDP stub (`172.20.0.40:2000`)
- Full PDP-10 OS integration remains the next Phase 2 step

### Phase 2.5: Centralized Logging (Complete ✅)

**Purpose**: Capture, parse, and persist logs from all ARPANET components for debugging and analysis.

**Infrastructure**:
- Modular Python package (`arpanet_logging/`)
- Real-time Docker log streaming
- 20GB persistent EBS volume ($2/month)
- JSON Lines structured format
- CLI management tool

**Status**: Production-ready, validated on AWS
- VAX collector with BSD 4.3 parser ✅
- Event detection and tagging ✅
- Statistics and indexing ✅

See `../arpanet_logging/README.md` for usage details.

### Phase 3: Build Integration (Future)

**Purpose**: Build pipeline depends on ARPANET for artifact movement:
- Compile `bradman.c` on VAX
- Transfer binary to PDP-10 via ARPANET FTP
- Execute or transfer back artifacts
- Include ARPANET logs in build output

**Prerequisites**: Phase 2.5 logging ✅ complete, Phase 2 PDP-10 integration pending.

## Directory Structure

```
arpanet/
├── README.md                    # This file
├── PHASE1-SUMMARY.md            # Phase 1 implementation details
├── TESTING-GUIDE.md             # Testing procedures
├── PHASE2-PLAN.md               # Phase 2 implementation plan/status
├── PHASE2-VALIDATION.md         # Phase 2 validation notes/findings
├── Dockerfile.imp               # IMP simulator container
├── Dockerfile.pdp10stub         # Phase 2.2 bootstrap host stub
├── configs/
│   ├── vax-network.ini         # SIMH VAX with networking enabled
│   ├── imp-phase1.ini          # Phase 1 IMP config
│   ├── imp1-phase2.ini         # Phase 2 IMP #1 config (VAX + MI1)
│   └── imp2.ini                # Phase 2 IMP #2 config (MI1 + future HI1)
└── scripts/
    ├── test-vax-imp.sh         # Test VAX→IMP connectivity
    └── test-phase2-imp-link.sh # Test Phase 2 IMP↔IMP modem link

build/arpanet/
├── imp1/                       # IMP #1 runtime data
└── logs/                       # Network logs and transcripts
```

## Usage

### Phase 1: Start VAX + IMP

```bash
# Build IMP container
docker-compose -f docker-compose.arpanet.phase1.yml build

# Start the network
docker-compose -f docker-compose.arpanet.phase1.yml up -d

# View logs
docker-compose -f docker-compose.arpanet.phase1.yml logs -f

# Connect to VAX console
telnet localhost 2323

# Connect to IMP console (debugging)
telnet localhost 2324

# Stop the network
docker-compose -f docker-compose.arpanet.phase1.yml down
```

### Phase 2 (Bootstrap): Start VAX + IMP1 + IMP2 + PDP10 stub

```bash
# Build Phase 2 containers
docker compose -f docker-compose.arpanet.phase2.yml build

# Start the network
docker compose -f docker-compose.arpanet.phase2.yml up -d

# Run automated Phase 2 initial test
bash arpanet/scripts/test-phase2-imp-link.sh

# Show Phase 2 logs
docker compose -f docker-compose.arpanet.phase2.yml logs -f imp1 imp2

# Stop Phase 2 network
docker compose -f docker-compose.arpanet.phase2.yml down
```

Equivalent Make targets:

```bash
make build-phase2
make up-phase2
make test-phase2
make logs-phase2
make down-phase2
```

### Testing VAX Connectivity

Once connected to VAX (telnet localhost 2323):

```bash
# Login as root (no password in base image)
login: root

# Check network interface
/etc/ifconfig de0

# Check routing table
netstat -rn

# Test IMP connectivity (if ping available)
ping 172.20.0.20
```

### AWS Testing

For architecture-specific testing on x86_64:

```bash
# Provision EC2 instance
make aws-up

# SSH into instance
make aws-ssh

# Run tests on EC2
cd brfid.github.io
docker-compose -f docker-compose.arpanet.phase1.yml build --progress=plain
make test

# Destroy instance when done
exit
make aws-down
```

See `test_infra/README.md` for AWS testing infrastructure details.

## Technical Details

### VAX Networking

The VAX/BSD system (4.3BSD) has:
- **de0**: DEC Ethernet (DEUNA/DELUA) interface
- **TCP/IP stack**: Full Berkeley networking
- **Tools**: `ifconfig`, `netstat`, `ping`, `ftp`, `telnet`
- **IMP driver**: 4.3BSD included native ARPANET support

### IMP Simulator

The IMP (Interface Message Processor) was the packet-switching router of ARPANET:
- **Hardware**: Honeywell 316/516 minicomputer
- **Firmware**: BBN-developed packet switching software
- **Protocol**: Original ARPANET 1822 protocol
- **Emulator**: SIMH H316 simulator

### Network Configuration

- **Subnet**: 172.20.0.0/16
- **VAX**: 172.20.0.10
- **IMP #1**: 172.20.0.20

## References

- [obsolescence/arpanet](https://github.com/obsolescence/arpanet) - Source project
- [SIMH Project](http://simh.trailing-edge.com/) - Hardware emulator
- [RFC 1822](https://tools.ietf.org/html/rfc1822) - ARPANET Host-IMP Interface
- [4.3BSD Networking](https://www.tuhs.org/Archive/Distributions/UCB/4.3BSD/) - VAX Unix

## Development Status

### Phase 1: Complete
- [x] Docker Compose architecture designed
- [x] VAX network configuration created
- [x] IMP Dockerfile scaffolded
- [x] AWS testing infrastructure set up
- [x] Integrate actual IMP firmware from upstream repo (impcode.simh, impconfig.simh)
- [x] IMP container builds successfully (h316 simulator compiles)
- [x] Both containers start and run
- [x] IMP connects to UDP port 2000
- [x] VAX boots and detects de0 network interface
- [x] Test VAX→IMP connectivity (Docker network operational, traffic flowing)
- [x] Validate ARPANET 1822 protocol communication (IMP sending 1822 messages)
- [x] Document successful connection in build log (see PHASE1-VALIDATION.md)

**Phase 1 validation complete (2026-02-07):**
- Fixed IMP Dockerfile build dependencies (added ca-certificates, libedit-dev, libpng-dev, curl)
- Successfully built h316 simulator from source
- Both VAX and IMP containers operational on AWS EC2 x86_64
- VAX de0 interface: 172.20.0.10/16, UP and RUNNING
- IMP HI1 interface: listening on UDP 2000, sending ARPANET 1822 protocol messages
- Docker network (172.20.0.0/16) with traffic flowing between containers
- All Phase 1 success criteria met

### Phase 2: Step 2.2 bootstrap in progress

- [x] Added IMP #2 container/config (`arpanet/configs/imp2.ini`)
- [x] Added Phase 2 IMP #1 config (`arpanet/configs/imp1-phase2.ini`)
- [x] Added `docker-compose.arpanet.phase2.yml` for VAX + IMP1 + IMP2 (+ PDP10 stub)
- [x] Added automated test script (`arpanet/scripts/test-phase2-imp-link.sh`) with HI1 checks
- [x] Added PDP10 host stub container (`arpanet/Dockerfile.pdp10stub`)
- [x] Wired IMP2 HI1 to host endpoint `172.20.0.40:2000`
- [x] Validated on AWS EC2 x86_64:
  - Containers up: `arpanet-vax`, `arpanet-imp1`, `arpanet-imp2`, `arpanet-pdp10`
  - IPs: `172.20.0.10`, `172.20.0.20`, `172.20.0.30`, `172.20.0.40`
  - MI1 packet send/receive visible in both IMP logs
  - HI1 packet send markers visible from IMP2

**Status**: Phase 1 complete; Phase 2 Step 2.1 complete; Step 2.2 host-link bootstrap validated.

See `PHASE1-VALIDATION.md` and `PHASE2-VALIDATION.md` for validation results, plus `PHASE1-SUMMARY.md` and `TESTING-GUIDE.md` for detailed procedures.

## Notes

This is experimental infrastructure for creating a "quiet technical signal" in the build process. The ARPANET integration demonstrates historical computing techniques while serving as a functional (if anachronistic) build pipeline component.
