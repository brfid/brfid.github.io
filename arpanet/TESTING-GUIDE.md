# ARPANET Testing Guide (Phase 1 + Phase 2 Initial)

## Prerequisites

This setup requires Docker with daemon access. Testing must be done on a machine with Docker installed and running (not in this Claude Code environment).

## Quick Start Testing

### Phase 2 Initial (Current Recommended for next-step testing)

This validates the current Phase 2 Step 2.2 bootstrap topology:

```
[VAX] ←→ [IMP-1] ←MI1/UDP:3001→ [IMP-2] ←HI1/UDP:2000→ [PDP10 stub]
```

```bash
# Build and start phase 2 initial topology
docker compose -f docker-compose.arpanet.phase2.yml build
docker compose -f docker-compose.arpanet.phase2.yml up -d

# Automated validation
bash arpanet/scripts/test-phase2-imp-link.sh

# Optional helpers
make build-phase2
make up-phase2
make test-phase2
make logs-phase2

# Consoles
telnet localhost 2323  # VAX
telnet localhost 2324  # IMP1
telnet localhost 2325  # IMP2
docker logs arpanet-pdp10 | tail -20  # PDP10 stub activity

# Stop
docker compose -f docker-compose.arpanet.phase2.yml down
```

**Phase 2 success criteria (bootstrap):**
- `arpanet-vax`, `arpanet-imp1`, `arpanet-imp2`, `arpanet-pdp10` are running
- IMP1 and IMP2 logs show MI1 startup markers
- IMP1 and IMP2 logs show ongoing MI1 packet send/receive activity
- IMP2 logs show HI1 startup markers / host-link activity for `172.20.0.40`

---

### Phase 1 (Legacy baseline)

### 1. Clone the Branch

```bash
git clone https://github.com/brfid/brfid.github.io.git
cd brfid.github.io
git checkout claude/arpanet-build-integration-uU9ZL
```

### 2. Build the Containers

```bash
# Using Docker Compose v2 (recommended)
docker compose -f docker-compose.arpanet.phase1.yml build

# Or using Docker Compose v1
docker-compose -f docker-compose.arpanet.phase1.yml build
```

**Expected build time**: 30-60 seconds
- VAX container: Pre-built image (pulled from Docker Hub)
- IMP container: Built from source (~20-30 seconds)

### 3. Start the Network

```bash
docker compose -f docker-compose.arpanet.phase1.yml up -d
```

**What this does:**
- Creates isolated network `arpanet-build` (172.20.0.0/16)
- Starts VAX container at 172.20.0.10
- Starts IMP container at 172.20.0.20
- Establishes UDP connection on port 2000

### 4. Run Automated Tests

```bash
./arpanet/scripts/test-vax-imp.sh
```

**Expected output:**
```
=========================================
ARPANET Phase 1 Connectivity Test
=========================================

Step 1: Checking if containers are running...
✓ Both VAX and IMP containers are running

Step 2: Checking VAX boot status...
[VAX boot logs...]

Step 3: Checking IMP status...
[IMP logs showing firmware load...]

Step 4: Checking network connectivity...
VAX IP: 172.20.0.10
IMP IP: 172.20.0.20

...
```

### 5. Manual Testing - VAX Console

```bash
# Connect to VAX
telnet localhost 2323

# Login (wait for login prompt, may take 30-60 seconds on first boot)
login: root
# (no password in base image)

# Check network interface
/etc/ifconfig de0

# Expected output:
de0: flags=63<UP,BROADCAST,NOTRAILERS,RUNNING>
        inet 172.20.0.10 netmask ffffff00 broadcast 172.20.0.255

# Check routing table
netstat -rn

# Test IMP connectivity (if ping available)
ping 172.20.0.20
```

### 6. Manual Testing - IMP Console

```bash
# Connect to IMP (separate terminal)
telnet localhost 2324

# You should see IMP diagnostic output
# Look for messages like:
# "IMP #1 starting..."
# "Host interface hi1 attached"
```

### 7. View Logs

```bash
# VAX logs
docker logs arpanet-vax

# IMP logs
docker logs arpanet-imp1 | less

# Follow logs in real-time
docker compose -f docker-compose.arpanet.phase1.yml logs -f
```

### 8. Stop the Network

```bash
docker compose -f docker-compose.arpanet.phase1.yml down
```

## Detailed Testing Scenarios

### Scenario 1: Basic Connectivity

**Goal**: Verify VAX can see IMP on the network

```bash
# On VAX console:
/etc/ifconfig de0
netstat -rn
netstat -i
```

**Success criteria:**
- `de0` interface shows as UP and RUNNING
- IP address configured: 172.20.0.10
- Netmask: 255.255.255.0
- No errors in interface statistics

### Scenario 2: IMP Host Interface

**Goal**: Verify IMP recognizes VAX as connected host

```bash
# Check IMP logs:
docker logs arpanet-imp1 | grep -i "host\|hi1"
```

**Success criteria:**
- `hi1 enabled` message
- `attach -u hi1 2000:172.20.0.10:2000` executed
- No "connection refused" or "unreachable" errors

### Scenario 3: UDP Communication

**Goal**: Verify UDP packets can flow between containers

```bash
# Monitor IMP with debug output:
docker logs arpanet-imp1 | grep -i "debug\|packet\|data"

# On VAX, attempt to generate network traffic:
# (exact commands depend on available tools in the VAX image)
```

### Scenario 4: Long-term Stability

**Goal**: Verify network stays up over time

```bash
# Leave running for 5-10 minutes
docker compose -f docker-compose.arpanet.phase1.yml up

# Monitor resource usage
docker stats arpanet-vax arpanet-imp1

# Check for crashes or restarts
docker ps -a | grep arpanet
```

## Troubleshooting

### Problem: VAX won't boot

```bash
# Check VAX logs
docker logs arpanet-vax

# Common issues:
# - Disk images not found (check base image)
# - Memory allocation failure
# - Configuration file errors
```

**Solution**: Verify the base image is correct:
```bash
docker images | grep simh-vaxbsd
```

### Problem: IMP firmware won't load

```bash
# Check IMP logs
docker logs arpanet-imp1

# Look for:
# - "impcode.simh" not found errors
# - Memory allocation errors
# - Syntax errors in .ini files
```

**Solution**: Verify firmware files are present:
```bash
ls -lh arpanet/configs/imp*.simh
```

### Problem: Containers can't communicate

```bash
# Check network
docker network inspect arpanet-build

# Verify both containers are on the network
# Check IP addresses match configuration
```

**Solution**: Restart with clean network:
```bash
docker compose -f docker-compose.arpanet.phase1.yml down
docker network prune
docker compose -f docker-compose.arpanet.phase1.yml up -d
```

### Problem: Port conflicts

**Error**: "port 2323 already in use"

**Solution**:
```bash
# Find what's using the port
lsof -i :2323  # macOS/Linux
netstat -ano | findstr :2323  # Windows

# Either stop that service or change ports in docker-compose.arpanet.phase1.yml
```

### Problem: VAX network interface not configured

The VAX might need manual network configuration on first boot.

**Solution**: Connect to VAX and run:
```bash
/etc/ifconfig de0 172.20.0.10 netmask 255.255.255.0 up
route add default 172.20.0.1
```

## Performance Expectations

### Boot Times
- **VAX**: 30-90 seconds (4.3BSD boot + init)
- **IMP**: 5-10 seconds (firmware load + initialization)

### Resource Usage
- **VAX**: ~100-200 MB RAM, <5% CPU
- **IMP**: ~20-50 MB RAM, <2% CPU
- **Network**: Minimal bandwidth (<1 Mbps)

### Disk Space
- **Images**: ~150 MB (VAX base image + IMP)
- **Runtime data**: <10 MB (logs, state)

## Success Indicators

✅ **Phase 1 is working if:**

1. Both containers start without errors
2. VAX boots to login prompt
3. IMP loads firmware successfully
4. `de0` interface shows as UP on VAX
5. No connection errors in IMP logs
6. Network `arpanet-build` exists with both containers
7. UDP ports 2000 are open on both containers

## Next Steps After Success

Once Phase 1 is validated:

1. **Document findings** - Note any issues or quirks
2. **Capture logs** - Save successful boot/connection logs
3. **Proceed with Phase 2.2** - Attach PDP-10 host to IMP #2 HI1
4. **Extend tests** - Verify multi-hop host traffic and eventual file transfer

## Phase 2 Preview

Phase 2 will add:
```
[VAX] ←→ [IMP-1] ←IMP-to-IMP→ [IMP-2] ←→ [PDP-10]
```

Testing will include:
- IMP routing table propagation
- Multi-hop packet forwarding
- FTP file transfer VAX → PDP-10
- Network monitoring and packet capture

## Reference Files

- `docker-compose.arpanet.phase1.yml` - Main orchestration
- `docker-compose.arpanet.phase2.yml` - Phase 2 bootstrap orchestration (VAX + IMP1 + IMP2 + PDP10 stub)
- `arpanet/configs/vax-network.ini` - VAX network config
- `arpanet/configs/imp-phase1.ini` - IMP configuration
- `arpanet/configs/imp1-phase2.ini` - IMP #1 Phase 2 configuration
- `arpanet/configs/imp2.ini` - IMP #2 Phase 2 configuration
- `arpanet/scripts/test-vax-imp.sh` - Automated test script
- `arpanet/scripts/test-phase2-imp-link.sh` - Phase 2 modem/host-link automated test script
- `arpanet/README.md` - Full documentation
- `arpanet/PHASE1-SUMMARY.md` - Implementation summary
- `arpanet/PHASE2-VALIDATION.md` - Latest Phase 2 (2.1 + 2.2 bootstrap) validation findings

## Getting Help

If you encounter issues:

1. Check container logs: `docker logs <container_name>`
2. Verify network: `docker network inspect arpanet-build`
3. Review configuration files in `arpanet/configs/`
4. Consult SIMH documentation: http://simh.trailing-edge.com/
5. Reference upstream project: https://github.com/obsolescence/arpanet

---

**Last Updated**: 2026-02-07
**Status**: Phase 1 complete, Phase 2 Step 2.2 host-link bootstrap validated on AWS x86_64
