# Local Testing Environment

Tools for testing ARPANET integration on local hardware (Raspberry Pi, development machines).

## Purpose

Local testing provides:
- Interactive debugging with full system access
- Faster iteration than CI/CD feedback loops
- Testing on actual deployment hardware

## Setup

### Prerequisites

1. Docker and Docker Compose installed
2. At least 2GB free disk space
3. Network access for pulling container images

### Initial Setup

```bash
# Run setup script
./setup.sh

# Verify environment
make check_env
```

## Usage

### Basic Testing

```bash
# Start ARPANET network
docker compose -f docker-compose.arpanet.phase1.yml up -d

# Wait for boot (VAX takes ~60s, IMP takes ~10s)
sleep 70

# Run connectivity tests
../docker/test_arpanet.py --mode connectivity

# View logs
docker logs arpanet-vax
docker logs arpanet-imp1

# Cleanup
docker compose -f docker-compose.arpanet.phase1.yml down -v
```

### Interactive Debugging

```bash
# Start network in foreground
docker compose -f docker-compose.arpanet.phase1.yml up

# In another terminal, connect to VAX console
telnet localhost 2323

# Or connect to IMP console
telnet localhost 2324
```

## Raspberry Pi Specific

Tested on Raspberry Pi 4 with Debian/Raspbian.

### Performance Notes
- VAX boot time: ~60-90 seconds
- IMP boot time: ~10-15 seconds
- Total ready time: ~90 seconds

### Common Issues

**Slow builds**: Use `--progress=plain` to see detailed output:
```bash
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
```

**Out of memory**: Increase swap or close other applications.

**Network conflicts**: Check for existing Docker networks:
```bash
docker network ls
docker network prune
```
