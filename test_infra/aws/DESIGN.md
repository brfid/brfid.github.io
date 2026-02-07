# AWS Testing Infrastructure Design

**Architecture**: Ephemeral EC2 instances with Infrastructure as Code (Terraform)

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

**Choice**: Terraform

**Rationale**:
- Industry standard, portfolio-relevant skill
- Declarative, version-controlled infrastructure
- State management handles resource lifecycle
- Provider-agnostic (could add other clouds later)
- Better for portfolio visibility than CloudFormation

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

**Method**: CloudWatch + Lambda (future) OR local timer script

**Timing**: 2 hours after creation
- Typical debugging session: 30-90 minutes
- 2 hours provides buffer without excessive cost
- User can extend if needed

**Implementation**: Phase 1 uses manual shutdown, Phase 2 adds automation

### 6. State Management

**Terraform State**: Local filesystem (project root ignored by git)

**Rationale**:
- Single user, no team collaboration
- S3 backend adds complexity without benefit
- `.terraform/` and `*.tfstate` in `.gitignore`

**Future**: Could add S3 backend if multi-user or CI/CD provisioning needed

### 7. Access Management

**SSH Key**: Existing key or generate new
- User provides public key path in terraform.tfvars
- Key pair created/imported in AWS
- Private key stored locally (not in repo)

**Session Manager**: Not used (adds complexity)
- Direct SSH simpler for debugging
- No bastion host needed

### 8. Cost Controls

**Estimated Monthly Cost** (2 hours/week usage):
```
EC2 (t3.medium):  8 hrs/month × $0.042/hr  = $0.34
EBS (30GB GP3):   30GB × $0.08/GB/month    = $2.40
Data Transfer:    Minimal (~$0.10)
─────────────────────────────────────────────────
Total:                                      ~$2.84/month
```

**Peak Cost** (10 hours/month heavy debugging):
```
EC2:              10 hrs × $0.042/hr        = $0.42
EBS:              30GB × $0.08/GB/month     = $2.40
─────────────────────────────────────────────────
Total:                                      ~$2.82/month
```

**Note**: EBS cost dominates because volume persists during Terraform destroy if not configured for deletion.

**Optimization**: EBS volume deleted on instance termination (configured in Terraform)

**Revised Monthly Cost**: ~$0.34 - $0.42 (EC2 only, ephemeral storage)

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
│    └─> terraform apply                          │
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
│    └─> SSH into instance                        │
│    └─> Interactive debugging                    │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│  $ make aws-down                                │
│    └─> terraform destroy                        │
│    └─> Instance terminated, EBS deleted         │
└─────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Manual Provisioning (Current)
- Manual EC2 launch via AWS console
- Manual Docker setup
- Manual git clone
- Status: Documented in aws/README.md

### Phase 2: Basic IaC (Next)
- Terraform configuration for EC2
- User data script for automated setup
- `make aws-up`, `make aws-ssh`, `make aws-down`
- Local state file
- Status: **Planned (this document)**

### Phase 3: Enhanced Automation (Future)
- CloudWatch alarm for auto-shutdown
- S3 bucket for artifacts
- Terraform backend in S3
- GitHub Actions integration (optional)

## File Structure

```
test_infra/aws/
├── README.md              # User-facing documentation
├── DESIGN.md             # This file - architecture decisions
├── setup.sh              # Bootstrap script (runs on instance)
├── terraform/
│   ├── main.tf           # Primary Terraform configuration
│   ├── variables.tf      # Input variables
│   ├── outputs.tf        # Output values (IP address, etc)
│   ├── terraform.tfvars.example  # Example configuration
│   └── user-data.sh      # Cloud-init script
└── scripts/
    ├── provision.sh      # Wrapper for terraform apply
    ├── connect.sh        # SSH connection helper
    └── teardown.sh       # Wrapper for terraform destroy
```

## Security Considerations

### Public SSH Access
- Security group allows SSH from 0.0.0.0/0
- **Risk**: Exposed to internet scanning/brute force
- **Mitigation**:
  - Use strong SSH keys (not passwords)
  - Instance is ephemeral (short-lived)
  - No sensitive data on instance
  - Could restrict to specific IP if needed (terraform.tfvars)

### IAM Permissions
- No IAM role needed for basic setup
- If S3 access needed later, use minimal permissions

### Secrets Management
- GitHub token passed via environment variable
- Not stored in Terraform or AMI
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
# Instance terminated, no ongoing cost
```

### Quick Test Without SSH

```bash
# Provision, run tests, destroy
make aws-test
# Runs: terraform apply → SSH → make test → terraform destroy
# Returns: test results
```

## Terraform Variables

Configurable via `terraform.tfvars`:

```hcl
# Required
aws_region = "us-east-1"
ssh_public_key_path = "~/.ssh/id_rsa.pub"

# Optional
instance_type = "t3.medium"        # Or t3.large for faster builds
root_volume_size = 30              # GB
allowed_ssh_cidrs = ["0.0.0.0/0"]  # Restrict if needed
git_branch = "claude/arpanet-build-integration-uU9ZL"
```

## Cost Optimization Strategies

### Current (Phase 2)
- Ephemeral instances (only pay when running)
- EBS deletion on termination
- Use smallest viable instance (t3.medium)

### Future Opportunities
- ARM instances (t4g.medium) - 20% cheaper
- Spot instances for non-interactive tests
- Regional cost comparison (us-east-1 vs us-west-2)
- Reserved capacity if usage increases

## Success Criteria

Phase 2 implementation is successful when:
- [ ] `make aws-up` provisions working instance in <2 minutes
- [ ] Instance has Docker pre-installed and configured
- [ ] Repo is cloned and on correct branch
- [ ] `make aws-ssh` connects without manual IP lookup
- [ ] `make aws-down` cleanly destroys all resources
- [ ] No manual steps required
- [ ] Cost remains under $5/month with typical usage

## References

- AWS EC2 Pricing: https://aws.amazon.com/ec2/pricing/on-demand/
- Terraform AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- Ubuntu Cloud Images: https://cloud-images.ubuntu.com/locator/ec2/
