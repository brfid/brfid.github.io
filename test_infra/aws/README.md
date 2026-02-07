# AWS Testing Environment

Ephemeral EC2 infrastructure for ARPANET integration testing, managed with Terraform.

## Quick Start

### Prerequisites

1. AWS account with EC2 access
2. AWS CLI configured (`aws configure`)
3. Terraform installed (>= 1.0)
4. SSH key pair available

### First-Time Setup

```bash
# 1. Create Terraform configuration
cd test_infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars

# 2. Edit terraform.tfvars with your SSH key paths
# Required: Update ssh_public_key_path and ssh_private_key_path

# 3. Initialize Terraform
terraform init
```

### Usage

```bash
# From project root

# Provision test instance (~90 seconds)
make aws-up

# SSH into instance (auto-connects)
make aws-ssh

# Destroy instance when done
make aws-down

# Or run tests remotely without SSH
make aws-test
```

## How It Works

1. **`make aws-up`** - Terraform provisions EC2 instance with:
   - Docker pre-installed
   - Repository cloned on correct branch
   - All dependencies ready
   - Takes ~90 seconds

2. **`make aws-ssh`** - Connects automatically, ready for:
   ```bash
   cd brfid.github.io
   docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
   make test
   ```

3. **`make aws-down`** - Destroys instance, stops costs

## Architecture

See [DESIGN.md](DESIGN.md) for detailed architecture decisions.

**Key Points**:
- Ephemeral instances (created on-demand, destroyed when done)
- Infrastructure as Code (Terraform, version controlled)
- Cost: ~$0.042/hour, ~$2-5/month typical usage
- Auto-configures via cloud-init (user-data script)

## Implementation

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for step-by-step build instructions.

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

## Typical Workflow

### Debugging GitHub Actions Failure

```bash
# 1. GitHub Actions fails on ARPANET build
# 2. Provision test instance
make aws-up
# Output: "Instance ready at: 3.45.67.89"
# Time: ~90 seconds

# 3. SSH into instance
make aws-ssh

# 4. Debug interactively
cd brfid.github.io
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
# Identify issue from build output

# 5. Fix issue locally, commit, push
git add arpanet/Dockerfile.imp
git commit -m "Fix IMP build issue"
git push

# 6. Verify fix
make build && make up
docker ps -a

# 7. Exit and destroy instance
exit
make aws-down
# No ongoing costs
```

### Quick Remote Test

```bash
# Provision, test, destroy - all automated
make aws-test
# Returns test results, destroys instance
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
