# AWS Testing Infrastructure Design

> **Archive notice (historical document)**
>
> This file captures an earlier design phase and is kept for project history.
> Some paths and status notes here are no longer current (for example references
> to `test_infra/aws/...`).
>
> For current implementation and usage, use:
> - `test_infra/README.md`
> - `test_infra/cdk/`
> - `test_infra/scripts/`

**Architecture**: Ephemeral EC2 instances with Infrastructure as Code (AWS CDK in Python)

## Overview

Automated, on-demand EC2 testing environment for ARPANET integration debugging. Instances are ephemeral (created when needed, destroyed when done) to minimize costs while maintaining professional infrastructure practices.

## Design Decisions

### 1. Ephemeral vs Persistent

**Choice**: Ephemeral instances with IaC

**Rationale**:
- ARPANET debugging is reactive (only needed when GitHub Actions fails)
- Average usage: 1-2 hours per week
- Cost: ~$2-5/month vs ~$20-50/month for persistent
- IaC makes provisioning fast (<2 minutes to working instance)
- No maintenance burden of keeping instance updated

### 2. Infrastructure as Code Tool

**Choice**: AWS CDK (Cloud Development Kit) with Python

**Rationale**:
- **Pure Python** - Aligns with project philosophy ("Python preferred when reasonable")
- **Type safety** - IDE autocomplete, type hints, catch errors before deploy
- **Modern** - AWS's recommended approach for infrastructure as code
- **Portfolio value** - Shows cutting-edge AWS expertise
- **Native AWS** - Better integration than provider-agnostic tools
- **Testable** - Can unit test infrastructure code
- **AWS-only constraint** - Project already decided on AWS-only testing

### 3. Instance Specifications

**Type**: t3.medium (2 vCPU, 4GB RAM)
- VAX emulation requires 4GB+ RAM
- Multi-stage Docker builds benefit from 2+ CPUs
- Cost: ~$0.042/hour in us-east-1

**AMI**: Ubuntu 22.04 LTS (latest)
- Consistent with GitHub Actions runners
- Docker official install script support
- Long-term support through 2027

**Storage**: 30GB GP3 EBS
- 20GB for OS + Docker images
- 10GB buffer for build artifacts
- GP3 for cost optimization

**Purchasing**: On-Demand (not Spot)
- Debugging sessions are interactive
- Spot interruption would lose work
- Cost difference minimal at <2hr sessions

### 4. Networking

**VPC**: Default VPC
- No need for custom networking
- Public IP for SSH access
- Internet gateway already configured

**Security Group**: Custom
- Inbound SSH (22) from anywhere (0.0.0.0/0)
- All outbound traffic allowed
- Simple, functional for debugging

### 5. Auto-Shutdown

**Method**: Manual for Phase 1, CloudWatch + Lambda for Phase 2

**Timing**: 2 hours typical session
- User destroys with `make aws-down`
- Future: Auto-shutdown after inactivity

### 6. State Management

**CDK State**: CloudFormation stack in AWS

**Rationale**:
- CDK uses CloudFormation under the hood
- State managed by AWS automatically
- No local state files to manage
- Built-in drift detection
- Easy to see resources in AWS console

### 7. Access Management

**SSH Key**: Existing key or generate new
- User provides public key path in cdk.context.json
- Key pair created in AWS
- Private key stored locally (not in repo)

### 8. Cost Controls

**Estimated Monthly Cost** (2 hours/week usage):
```
EC2 (t3.medium):  8 hrs/month × $0.042/hr  = $0.34
EBS (30GB GP3):   Deleted on termination   = $0.00
Data Transfer:    Minimal                  = $0.10
─────────────────────────────────────────────────
Total:                                      ~$0.44/month
```

**Peak Cost** (10 hours/month heavy debugging):
```
EC2:              10 hrs × $0.042/hr        = $0.42
Data Transfer:    Minimal                   = $0.10
─────────────────────────────────────────────────
Total:                                      ~$0.52/month
```

**Note**: EBS deleted on instance termination (ephemeral storage)

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│  GitHub Actions (fails)                         │
│  └─> Developer needs to debug                   │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  Local Machine                                  │
│  $ make aws-up                                  │
│    └─> cdk deploy (Python)                      │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  AWS CloudFormation                             │
│  Creates stack with:                            │
│  - EC2 Instance (t3.medium)                     │
│  - Security Group                               │
│  - SSH Key Pair                                 │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  AWS EC2 (t3.medium, Ubuntu 22.04)              │
│  ┌───────────────────────────────────────────┐  │
│  │ User Data Script (cloud-init)             │  │
│  │ 1. Install Docker                         │  │
│  │ 2. Clone repo                             │  │
│  │ 3. Checkout branch                        │  │
│  │ 4. Run test_infra/aws/setup.sh            │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Ready for: make build, make up, debugging      │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  $ make aws-ssh                                 │
│    └─> SSH into instance (Python script)        │
│    └─> Interactive debugging                    │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  $ make aws-down                                │
│    └─> cdk destroy (Python)                     │
│    └─> CloudFormation deletes all resources     │
└─────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Basic CDK (Next)
- CDK app and stack definition (Python)
- EC2 instance with user data
- Security group and SSH key
- Python scripts: provision.py, connect.py, destroy.py
- `make aws-up`, `make aws-ssh`, `make aws-down`
- Status: **In Progress**

### Phase 2: Enhanced Automation (Future)
- CloudWatch alarm for auto-shutdown
- S3 bucket for artifacts
- GitHub Actions integration (optional)
- SNS notifications

## File Structure

```
test_infra/aws/
├── README.md              # User-facing documentation
├── DESIGN.md             # This file - architecture decisions
├── IMPLEMENTATION.md     # Implementation guide
├── setup.sh              # Bootstrap script (runs on instance)
├── cdk/
│   ├── app.py            # CDK entry point
│   ├── arpanet_stack.py  # Stack definition (EC2, SG, etc)
│   ├── cdk.json          # CDK configuration
│   ├── requirements.txt  # Python dependencies (aws-cdk-lib, etc)
│   └── user_data.sh      # Cloud-init script
└── scripts/
    ├── provision.py      # Deploy CDK stack
    ├── connect.py        # SSH connection helper
    ├── destroy.py        # Destroy CDK stack
    └── status.py         # Check instance status
```

## Security Considerations

### Public SSH Access
- Security group allows SSH from 0.0.0.0/0
- **Risk**: Exposed to internet scanning/brute force
- **Mitigation**:
  - Use strong SSH keys (not passwords)
  - Instance is ephemeral (short-lived)
  - No sensitive data on instance
  - Could restrict to specific IP in cdk.context.json

### IAM Permissions
- No IAM role needed for basic setup
- If S3 access needed later, use minimal permissions

### Secrets Management
- GitHub token passed via environment variable
- Not stored in CDK code or AMI
- Injected at runtime via user data

## Usage Workflow

### Typical Debugging Session

```bash
# 1. GitHub Actions fails
# 2. Provision test instance
make aws-up
# Output: "Instance ready at: 3.45.67.89"
# Time: ~90 seconds

# 3. SSH into instance
make aws-ssh
# Auto-connects to instance

# 4. Debug ARPANET build
cd brfid.github.io
docker compose -f docker-compose.arpanet.phase1.yml build --progress=plain
# Watch build process, identify errors

# 5. Fix issues, commit, push
git add arpanet/Dockerfile.imp
git commit -m "Fix IMP build issue"
git push

# 6. Verify fix locally
make build && make up
docker ps -a

# 7. Exit and destroy instance
exit
make aws-down
# CloudFormation deletes all resources, no ongoing cost
```

## CDK Context Configuration

Configurable via `cdk.context.json` (gitignored):

```json
{
  "ssh_public_key_path": "~/.ssh/id_rsa.pub",
  "ssh_private_key_path": "~/.ssh/id_rsa",
  "instance_type": "t3.medium",
  "root_volume_size": 30,
  "allowed_ssh_cidrs": ["0.0.0.0/0"],
  "git_branch": "claude/arpanet-build-integration-uU9ZL"
}
```

## Cost Optimization Strategies

### Current (Phase 1)
- Ephemeral instances (only pay when running)
- EBS deletion on termination
- Use smallest viable instance (t3.medium)

### Future Opportunities
- ARM instances (t4g.medium) - 20% cheaper
- Spot instances for non-interactive tests
- Regional cost comparison (us-east-1 vs us-west-2)
- Reserved capacity if usage increases

## Success Criteria

Phase 1 implementation is successful when:
- [ ] `make aws-up` provisions working instance in <2 minutes
- [ ] Instance has Docker pre-installed and configured
- [ ] Repo is cloned and on correct branch
- [ ] `make aws-ssh` connects without manual IP lookup
- [ ] `make aws-down` cleanly destroys all resources
- [ ] No manual steps required
- [ ] Cost remains under $5/month with typical usage
- [ ] All code is Python (no HCL/Terraform)

## CDK vs Terraform Comparison

| Feature | CDK (Chosen) | Terraform |
|---------|-------------|-----------|
| Language | Python | HCL |
| Type Safety | Yes (mypy) | Limited |
| IDE Support | Full | Basic |
| Cloud Support | AWS only | Multi-cloud |
| State Management | CloudFormation | Local/Remote |
| Learning Curve | Python devs: Easy | New language |
| Portfolio Value | Modern/Cutting-edge | Industry standard |
| Testing | Unit tests in Python | Limited |

## References

- AWS CDK Python: https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html
- AWS EC2 Pricing: https://aws.amazon.com/ec2/pricing/on-demand/
- CDK EC2 Module: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2.html
