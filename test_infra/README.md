# AWS Testing Environment

Ephemeral EC2 infrastructure for ARPANET integration testing, managed with AWS CDK (Python).

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
npm install -g aws-cdk

# 2. Create CDK context file
cd test_infra/aws/cdk
cp cdk.context.json.example cdk.context.json

# 3. Edit cdk.context.json with your SSH key paths
# Required: Update ssh_public_key_path and ssh_private_key_path

# 4. Install Python dependencies
pip3 install -r requirements.txt

# 5. Bootstrap CDK (one-time per AWS account/region)
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
   - EC2 instance (t3.medium, Ubuntu 22.04)
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

See [DESIGN.md](DESIGN.md) for detailed architecture decisions.

**Key Points**:
- Ephemeral instances (created on-demand, destroyed when done)
- Infrastructure as Code (AWS CDK in Python, not Terraform)
- Cost: ~$0.042/hour, ~$0.50/month typical usage
- Auto-configures via cloud-init (user-data script)
- All Python (CDK + helper scripts)

## Implementation

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for step-by-step build instructions.

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
test_infra/aws/
├── README.md              # This file
├── DESIGN.md              # Architecture decisions
├── IMPLEMENTATION.md      # Build instructions
├── setup.sh               # Bootstrap script (runs on instance)
├── cdk/
│   ├── app.py             # CDK entry point
│   ├── arpanet_stack.py   # Stack definition (EC2, SG, etc)
│   ├── cdk.json           # CDK configuration
│   ├── requirements.txt   # Python dependencies
│   ├── user_data.sh       # Cloud-init script
│   └── cdk.context.json.example  # Config template
└── scripts/
    ├── provision.py       # Deploy stack
    ├── connect.py         # SSH helper
    ├── destroy.py         # Destroy stack
    └── status.py          # Check status
```

## Configuration

Edit `cdk/cdk.context.json`:

```json
{
  "ssh_public_key_path": "~/.ssh/id_rsa.pub",
  "ssh_private_key_path": "~/.ssh/id_rsa",
  "instance_type": "t3.medium",
  "root_volume_size": 30,
  "allowed_ssh_cidrs": ["0.0.0.0/0"],
  "git_branch": "claude/arpanet-build-integration-uU9ZL",
  "aws_region": "us-east-1"
}
```

## Cost

**Typical debugging session** (2 hours):
- EC2: $0.084
- **Total: ~$0.08 per session**

**Monthly** (2 sessions/week):
- ~$0.70/month

## Troubleshooting

### CDK Issues

**`cdk` command not found**
```bash
npm install -g aws-cdk
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
- Verify key permissions: `chmod 600 ~/.ssh/id_rsa`

### CloudFormation Issues

**Stack creation fails**
- Check AWS Console → CloudFormation → ArpanetTestStack
- View Events tab for error details
- Check CloudWatch Logs for user-data output

## Next Steps

After getting instance working:
1. Debug current ARPANET IMP build failure
2. Document fix in MEMORY.md
3. Consider enhancements:
   - Auto-shutdown Lambda
   - S3 artifact storage
   - CloudWatch dashboards
