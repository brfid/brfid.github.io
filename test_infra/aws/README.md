# AWS Testing Environment

Setup and run ARPANET integration tests on AWS EC2.

## Quick Start

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
./test_infra/aws/setup.sh

# 6. Build and test
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
docker compose -f docker-compose.arpanet.phase1.yml up -d
docker ps -a
docker logs arpanet-vax
docker logs arpanet-imp1

# 7. Run automated tests
./test_infra/docker/test_arpanet.py --verbose
```

## Recommended Instance

- **Type**: t3.medium (2 vCPU, 4GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20GB GP3
- **Region**: us-east-1 (lowest cost)
- **Security Group**: Allow SSH (port 22) from your IP

## Cost Estimate

- ~$0.04/hour for t3.medium
- ~$0.10/GB/month for storage
- Total: ~$1-2 for typical debugging session

## Prerequisites

- AWS account with EC2 access
- SSH key pair configured
- Docker and Docker Compose (installed by setup.sh)
- At least 2GB free disk space
- 4GB+ RAM (VAX emulation is memory-intensive)

## Usage

### Interactive Debugging

```bash
# Start network in foreground
docker compose -f docker-compose.arpanet.phase1.yml up

# In another terminal, connect to consoles
telnet localhost 2323  # VAX
telnet localhost 2324  # IMP
```

### Automated Testing

```bash
# Run all tests
make test

# Run specific test modes
./test_infra/docker/test_arpanet.py --mode build
./test_infra/docker/test_arpanet.py --mode connectivity
./test_infra/docker/test_arpanet.py --mode logs
```

## Common Issues

**Slow builds**: Use `--progress=plain` to see detailed output:
```bash
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
```

**Out of memory**: Use larger instance type (t3.large has 8GB RAM).

**Network conflicts**: Check for existing Docker networks:
```bash
docker network ls
docker network prune
```

**Permission denied**: Ensure user is in docker group:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```
