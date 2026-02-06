# Local Development Testing

Tools for testing ARPANET integration on local development machines.

## Purpose

Local testing provides:
- Interactive debugging with full system access
- Faster iteration than CI/CD feedback loops
- Immediate feedback during development

## Setup

### Prerequisites

1. Docker and Docker Compose installed
2. At least 2GB free disk space
3. Network access for pulling container images
4. 4GB+ RAM recommended (VAX emulation is memory-intensive)

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

## Common Issues

**Slow builds**: Use `--progress=plain` to see detailed output:
```bash
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
```

**Out of memory**: Close other applications or increase Docker memory limit.

**Network conflicts**: Check for existing Docker networks:
```bash
docker network ls
docker network prune
```

## Cloud Testing (AWS)

For remote debugging when GitHub Actions feedback is too slow or local testing isn't sufficient.

### Quick Start

```bash
# 1. Launch EC2 instance (t3.medium, Ubuntu 22.04)
# 2. SSH into instance
ssh -i your-key.pem ubuntu@ec2-instance-ip

# 3. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu
# Log out and back in for group changes

# 4. Clone repo
git clone https://github.com/brfid/brfid.github.io.git
cd brfid.github.io
git checkout claude/arpanet-build-integration-uU9ZL

# 5. Run setup
./test_infra/local/setup.sh

# 6. Build and test
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
docker compose -f docker-compose.arpanet.phase1.yml up -d
docker ps -a
docker logs arpanet-vax
docker logs arpanet-imp1
```

### Recommended Instance
- **Type**: t3.medium (2 vCPU, 4GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20GB GP3
- **Region**: us-east-1 (lowest cost)

### Cost Estimate
- ~$0.04/hour for t3.medium
- ~$0.10/GB/month for storage
- Total: ~$1-2 for typical debugging session
