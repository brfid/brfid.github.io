# AWS Testing Environment

> Retired path (2026-02-15): `test_infra` orchestration code is no longer part
> of active repo workflows. Keep this document as historical context only.
> Current lifecycle ownership is in `edcloud`:
> `https://github.com/brfid/edcloud/blob/main/SETUP.md`.

**Purpose**: Development and debugging environment for ARPANET orchestration that will run in the build pipeline.

## Why AWS Testing?

ARPANET integration requires x86_64 Docker images, but development happens on ARM devices (Raspberry Pi). AWS EC2 provides on-demand x86_64 instances for:
- Testing ARPANET orchestration before deploying to GitHub Actions
- Debugging pipeline issues interactively
- Iterating on new ARPANET nodes or protocols

**Workflow**: Develop on AWS EC2 → Deploy to GitHub Actions → Debug on AWS EC2 as needed

This infrastructure remains in place as a permanent development tool whenever the pipeline is expanded or debugged.

## Design: Orchestration from Small Linux Systems

This infrastructure is **controlled from resource-constrained devices** (Raspberry Pi, low-power ARM systems, old laptops) while leveraging cloud computing for architecture-specific testing.

**Architecture:**
```
┌─────────────────────────────┐
│  Controller                 │
│  (Pi, aarch64, low-power)   │
│  ┌─────────────────────┐    │
│  │ Python CDK Scripts  │    │
│  │ AWS SDK (boto3)     │    │
│  └─────────────────────┘    │
│          │ API calls         │
└──────────┼──────────────────┘
           │ HTTPS
┌──────────▼──────────────────┐
│  AWS Cloud                  │
│  ┌─────────────────────┐    │
│  │ EC2 x86_64          │    │
│  │ - Docker builds     │    │
│  │ - ARPANET testing   │    │
│  │ - Architecture work │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
```

**Benefits:**
- **No local resource constraints** - Heavy Docker builds run on EC2
- **Architecture flexibility** - Test x86_64-specific code from ARM devices
- **Cost-effective** - Pay only when running tests (~$0.04/hour)
- **Pure Python** - All orchestration scripts use Python + boto3
- **Portable** - Works from any system with Python + AWS CLI

## Quick Start

### Prerequisites

1. AWS account with EC2 access
2. AWS CLI configured (`aws configure`)
3. Python 3.8+ installed
4. Node.js installed (for CDK CLI)
5. SSH key pair available

### First-Time Setup

```bash
# 1. Install CDK CLI
sudo npm install -g aws-cdk

# 2. Create CDK context file
cd test_infra/cdk
cp cdk.context.json.example cdk.context.json

# 3. Edit cdk.context.json with your SSH key paths
# Required: Update ssh_public_key_path and ssh_private_key_path

# 4. Install Python dependencies (in project venv)
.venv/bin/pip install -r requirements.txt

# 5. Bootstrap CDK (one-time per AWS account/region)
cd ../../  # Back to project root
cdk bootstrap

# 6. Test CDK configuration
cdk synth
```

### Usage

```bash
# From project root

# Provision test instance (~2-3 minutes)
make aws-up

# SSH into instance (auto-connects)
make aws-ssh

# Check instance status
make aws-status

# Destroy instance when done
make aws-down
```

## How It Works

1. **`make aws-up`** - CDK deploys CloudFormation stack with:
   - EC2 instance (t3.medium, Ubuntu 22.04, x86_64)
   - Docker pre-installed
   - Repository cloned on correct branch
   - All dependencies ready
   - Takes ~2-3 minutes

2. **`make aws-ssh`** - Connects automatically, ready for:
   ```bash
   cd brfid.github.io
   docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
   make test
   ```

3. **`make aws-down`** - CDK destroys CloudFormation stack, stops costs

## Architecture

**Key Points:**
- **Ephemeral instances** - Created on-demand, destroyed when done
- **Infrastructure as Code** - AWS CDK in Python (not Terraform)
- **Cost-effective** - ~$0.042/hour, ~$0.50/month typical usage
- **Auto-configures** - cloud-init (user-data script) sets up environment
- **Python-first ops** - CDK + helper scripts + boto3, including logs-volume management

## Implementation

The test infrastructure uses:
- **AWS CDK (Python)** for infrastructure definitions
- **CloudFormation** for stack management (CDK transpiles to CFN)
- **boto3** for AWS API interactions
- **cloud-init** for instance bootstrapping

See `cdk/` directory for implementation details.

## Typical Workflow

### Debugging GitHub Actions Failure

```bash
# 1. GitHub Actions fails on ARPANET build
# 2. Provision test instance
make aws-up
# Output: CloudFormation stack details, SSH command
# Time: ~2-3 minutes

# 3. SSH into instance
make aws-ssh

# 4. Debug interactively
cd brfid.github.io
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
# Identify issue from build output

# 5. Fix issue (either on instance or locally), commit, push
git add arpanet/Dockerfile.imp
git commit -m "Fix IMP build issue"
git push

# 6. Verify fix
make build && make up
docker ps -a

# 7. Exit and destroy instance
exit
make aws-down
# CloudFormation deletes all resources, no ongoing costs
```

## File Structure

```
test_infra/
├── README.md              # This file
├── setup.sh               # Bootstrap script (runs on instance)
├── cdk/
│   ├── app.py             # CDK entry point
│   ├── arpanet_stack.py   # Stack definition (EC2, SG, etc)
│   ├── cdk.json           # CDK configuration
│   ├── requirements.txt   # Python dependencies
│   ├── user_data.sh       # Cloud-init script
│   └── cdk.context.json.example  # Config template
├── scripts/
│   ├── provision.py       # Deploy stack
│   ├── connect.py         # SSH helper
│   ├── destroy.py         # Destroy stack
│   ├── status.py          # Check status
│   └── manage_logs_volume.py # Logs volume setup/retention cleanup
└── docker/                # Docker integration tests
```

## Configuration

Edit `cdk/cdk.context.json`:

```json
{
  "ssh_public_key_path": "~/.ssh/id_ed25519.pub",
  "ssh_private_key_path": "~/.ssh/id_ed25519",
  "instance_type": "t3.medium",
  "root_volume_size": 30,
  "logs_volume_size": 8,
  "persist_logs_volume": true,
  "logs_retention_days": 14,
  "allowed_ssh_cidrs": ["0.0.0.0/0"],
  "git_branch": "main",
  "aws_region": "us-east-1"
}
```

### Logs Volume Configuration

- `logs_volume_size` (GB): set to `0` to disable the dedicated logs volume.
- `persist_logs_volume`: when `true`, logs volume survives instance termination.
- `logs_retention_days`: delete entries older than N days from `builds/` and `active/`.

The bootstrap now uses `test_infra/scripts/manage_logs_volume.py` for disk discovery and cleanup.
It does **not** rely on hardcoded disk size matching.

## Cost

**Typical debugging session** (2 hours):
- EC2: $0.084
- **Total: ~$0.08 per session**

**Monthly** (2 sessions/week):
- ~$0.70/month

**No charges when instances are destroyed**

## Troubleshooting

### CDK Issues

**`cdk` command not found**
```bash
sudo npm install -g aws-cdk
cdk --version
```

**Bootstrap fails**
```bash
aws sts get-caller-identity  # Check credentials
cdk bootstrap  # Re-run bootstrap
```

**`cdk synth` fails**
- Verify cdk.context.json exists and is valid JSON
- Check SSH key paths are correct
- Check Python syntax in app.py, arpanet_stack.py

### SSH Issues

**Can't connect**
- Wait 3-4 minutes for user-data to complete
- Check `make aws-status` shows CREATE_COMPLETE
- Verify key permissions: `chmod 600 ~/.ssh/id_ed25519`

### CloudFormation Issues

**Stack creation fails**
- Check AWS Console → CloudFormation → ArpanetTestStack
- View Events tab for error details
- Check CloudWatch Logs for user-data output

## Future Enhancements

- Auto-shutdown Lambda (prevent forgotten instances)
- S3 artifact storage (save build outputs)
- CloudWatch dashboards (metrics and monitoring)
- Multi-region support
