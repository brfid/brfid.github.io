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

**Testing**: AWS EC2 x86_64 instances used for architecture-specific testing (see `test_infra/`)

### Phase 2: Two Hosts + IMPs (Future)

```
[VAX/BSD] ←→ [IMP-1] ←→ [IMP-2] ←→ [PDP-10/ITS]
```

**Purpose**: Create minimal but authentic ARPANET topology with file transfer capability between hosts.

### Phase 3: Build Integration (Future)

**Purpose**: Build pipeline depends on ARPANET for artifact movement:
- Compile `bradman.c` on VAX
- Transfer binary to PDP-10 via ARPANET FTP
- Execute or transfer back artifacts
- Include network logs in build output

## Directory Structure

```
arpanet/
├── README.md                    # This file
├── PHASE1-SUMMARY.md            # Phase 1 implementation details
├── TESTING-GUIDE.md             # Testing procedures
├── Dockerfile.imp               # IMP simulator container
├── configs/
│   ├── vax-network.ini         # SIMH VAX with networking enabled
│   └── imp1.ini                # IMP #1 configuration
└── scripts/
    ├── test-vax-imp.sh         # Test VAX→IMP connectivity
    └── start-arpanet.sh        # Launch full network

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

### Phase 1: ✅ Complete
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

**✅ Phase 1 Validation Complete (2026-02-07):**
- Fixed IMP Dockerfile build dependencies (added ca-certificates, libedit-dev, libpng-dev, curl)
- Successfully built h316 simulator from source
- Both VAX and IMP containers operational on AWS EC2 x86_64
- VAX de0 interface: 172.20.0.10/16, UP and RUNNING
- IMP HI1 interface: listening on UDP 2000, sending ARPANET 1822 protocol messages
- Docker network (172.20.0.0/16) with traffic flowing between containers
- All Phase 1 success criteria met

**Status**: ✅ Phase 1 operational, ready for Phase 2 planning

See `PHASE1-VALIDATION.md` for complete validation results, `PHASE1-SUMMARY.md` and `TESTING-GUIDE.md` for detailed documentation.

## Notes

This is experimental infrastructure for creating a "quiet technical signal" in the build process. The ARPANET integration demonstrates historical computing techniques while serving as a functional (if anachronistic) build pipeline component.
