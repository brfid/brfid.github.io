# ARPANET Build Integration

This directory contains the infrastructure for integrating ARPANET components into the build pipeline. The goal is to create a phased approach that slowly adds ARPANET components until there's an authentic 1970s network connection inside the build process.

## Overview

The integration is based on the [obsolescence/arpanet](https://github.com/obsolescence/arpanet) project, which recreates the ARPANET circa 1972-73 using SIMH emulation of period-accurate hardware.

## Architecture

### Phase 1: VAX + IMP (Current)

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

### Phase 2: Two Hosts + IMPs (Planned)

```
[VAX/BSD] ←→ [IMP-1] ←→ [IMP-2] ←→ [PDP-10/ITS]
```

**Purpose**: Create minimal but authentic ARPANET topology with file transfer capability between hosts.

### Phase 3: Build Integration (Planned)

**Purpose**: Build pipeline depends on ARPANET for artifact movement:
- Compile `bradman.c` on VAX
- Transfer binary to PDP-10 via ARPANET FTP
- Execute or transfer back artifacts
- Include network logs in build output

## Directory Structure

```
arpanet/
├── README.md                    # This file
├── Dockerfile.imp               # IMP simulator container
├── Dockerfile.pdp10             # PDP-10 host (Phase 2)
├── Dockerfile.server            # Python simh-server bridge (Phase 2)
├── configs/
│   ├── vax-network.ini         # SIMH VAX with networking enabled
│   ├── imp1.ini                # IMP #1 configuration
│   └── imp2.ini                # IMP #2 configuration (Phase 2)
└── scripts/
    ├── test-vax-imp.sh         # Test VAX→IMP connectivity
    └── start-arpanet.sh        # Launch full network

build/arpanet/
├── imp1/                       # IMP #1 runtime data
├── imp2/                       # IMP #2 runtime data
├── pdp10/                      # PDP-10 runtime data
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

### Build Integration

Once Phase 1 is validated, integrate with build pipeline:

```bash
# Run build with ARPANET mode (future)
resume-gen --out site --with-vax --vax-mode arpanet
```

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
- **IMP #2**: 172.20.0.30 (Phase 2)
- **PDP-10**: 172.20.0.40 (Phase 2)
- **simh-server**: 172.20.0.5 (Phase 2)

## References

- [obsolescence/arpanet](https://github.com/obsolescence/arpanet) - Source project
- [SIMH Project](http://simh.trailing-edge.com/) - Hardware emulator
- [RFC 1822](https://tools.ietf.org/html/rfc1822) - ARPANET Host-IMP Interface
- [4.3BSD Networking](https://www.tuhs.org/Archive/Distributions/UCB/4.3BSD/) - VAX Unix

## Development Status

- [x] Phase 1 Docker Compose architecture designed
- [x] VAX network configuration created
- [x] IMP Dockerfile scaffolded
- [ ] Integrate actual IMP firmware from upstream repo
- [ ] Test VAX→IMP connectivity
- [ ] Validate network interface configuration
- [ ] Document successful connection in build log
- [ ] Design Phase 2 architecture
- [ ] Implement build pipeline integration

## Notes

This is experimental infrastructure for creating a "quiet technical signal" in the build process. The ARPANET integration demonstrates historical computing techniques while serving as a functional (if anachronistic) build pipeline component.
