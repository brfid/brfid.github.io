# AWS Testing Infrastructure - Implementation Plan

Step-by-step plan to build ephemeral EC2 testing with Terraform.

## Prerequisites

- AWS account with EC2 access
- AWS CLI configured with credentials
- Terraform installed (>= 1.0)
- SSH key pair available

## Implementation Steps

### Step 1: Terraform Configuration Files

Create the following files in `test_infra/aws/terraform/`:

#### 1.1 `main.tf` - Core Infrastructure

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source for latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security group for SSH access
resource "aws_security_group" "arpanet_test" {
  name        = "arpanet-test-sg"
  description = "Security group for ARPANET testing instance"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name    = "arpanet-test"
    Project = "brfid.github.io"
    Purpose = "ARPANET debugging"
  }
}

# SSH key pair
resource "aws_key_pair" "arpanet_test" {
  key_name   = "arpanet-test-key"
  public_key = file(var.ssh_public_key_path)

  tags = {
    Name    = "arpanet-test"
    Project = "brfid.github.io"
  }
}

# EC2 instance
resource "aws_instance" "arpanet_test" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.arpanet_test.key_name

  vpc_security_group_ids = [aws_security_group.arpanet_test.id]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/user-data.sh", {
    git_repo   = var.git_repo
    git_branch = var.git_branch
  })

  tags = {
    Name    = "arpanet-test"
    Project = "brfid.github.io"
    Purpose = "ARPANET debugging"
  }

  # Wait for instance to be ready
  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait"
    ]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = self.public_ip
      private_key = file(var.ssh_private_key_path)
      timeout     = "5m"
    }
  }
}
```

#### 1.2 `variables.tf` - Input Variables

```hcl
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 30
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key"
  type        = string
}

variable "ssh_private_key_path" {
  description = "Path to SSH private key"
  type        = string
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "git_repo" {
  description = "Git repository URL"
  type        = string
  default     = "https://github.com/brfid/brfid.github.io.git"
}

variable "git_branch" {
  description = "Git branch to checkout"
  type        = string
  default     = "claude/arpanet-build-integration-uU9ZL"
}
```

#### 1.3 `outputs.tf` - Output Values

```hcl
output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.arpanet_test.id
}

output "instance_public_ip" {
  description = "Public IP address"
  value       = aws_instance.arpanet_test.public_ip
}

output "instance_public_dns" {
  description = "Public DNS name"
  value       = aws_instance.arpanet_test.public_dns
}

output "ssh_command" {
  description = "SSH connection command"
  value       = "ssh -i ${var.ssh_private_key_path} ubuntu@${aws_instance.arpanet_test.public_ip}"
}
```

#### 1.4 `user-data.sh` - Cloud-Init Script

```bash
#!/bin/bash
set -e

# Log output
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== ARPANET Test Instance Setup ==="
echo "Starting at: $(date)"

# Update system
echo "Updating system..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# Install Docker Compose (latest)
echo "Installing Docker Compose..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -oP '"tag_name": "\K(.*)(?=")')
curl -L "https://github.com/docker/compose/releases/download/$${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install additional tools
echo "Installing additional tools..."
apt-get install -y git make python3 python3-pip telnet netcat-openbsd

# Clone repository as ubuntu user
echo "Cloning repository..."
su - ubuntu -c "git clone ${git_repo} /home/ubuntu/brfid.github.io"
su - ubuntu -c "cd /home/ubuntu/brfid.github.io && git checkout ${git_branch}"

# Run setup script
echo "Running setup script..."
su - ubuntu -c "cd /home/ubuntu/brfid.github.io && ./test_infra/aws/setup.sh"

# Pull VAX image to save time
echo "Pre-pulling VAX Docker image..."
su - ubuntu -c "docker pull jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215"

echo "Setup complete at: $(date)"
echo "Instance ready for testing"
```

#### 1.5 `terraform.tfvars.example` - Example Configuration

```hcl
# Copy to terraform.tfvars and customize

# AWS Configuration
aws_region = "us-east-1"

# SSH Keys (REQUIRED - update these paths)
ssh_public_key_path  = "~/.ssh/id_rsa.pub"
ssh_private_key_path = "~/.ssh/id_rsa"

# Instance Configuration (optional overrides)
# instance_type = "t3.medium"
# root_volume_size = 30

# Security (optional - restrict SSH access)
# allowed_ssh_cidrs = ["1.2.3.4/32"]  # Your IP only

# Git Configuration (optional overrides)
# git_repo = "https://github.com/brfid/brfid.github.io.git"
# git_branch = "claude/arpanet-build-integration-uU9ZL"
```

### Step 2: Helper Scripts

Create in `test_infra/aws/scripts/`:

#### 2.1 `provision.sh`

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/../terraform"

echo "=== Provisioning ARPANET Test Instance ==="
terraform init
terraform apply -auto-approve

echo ""
echo "=== Instance Ready ==="
terraform output ssh_command
```

#### 2.2 `connect.sh`

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/../terraform"

if [ ! -f terraform.tfstate ]; then
    echo "Error: No active instance (run 'make aws-up' first)"
    exit 1
fi

SSH_CMD=$(terraform output -raw ssh_command 2>/dev/null)

if [ -z "$SSH_CMD" ]; then
    echo "Error: Could not get SSH command from Terraform"
    exit 1
fi

echo "Connecting to ARPANET test instance..."
eval $SSH_CMD
```

#### 2.3 `teardown.sh`

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/../terraform"

echo "=== Destroying ARPANET Test Instance ==="
terraform destroy -auto-approve

echo "Instance destroyed successfully"
```

#### 2.4 `test_remote.sh`

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/../terraform"

if [ ! -f terraform.tfstate ]; then
    echo "Error: No active instance (run 'make aws-up' first)"
    exit 1
fi

INSTANCE_IP=$(terraform output -raw instance_public_ip)
SSH_KEY=$(terraform output -json | jq -r '.ssh_command.value' | grep -oP '(?<=-i )\S+')

echo "Running tests on remote instance..."
ssh -i "$SSH_KEY" ubuntu@"$INSTANCE_IP" << 'ENDSSH'
cd ~/brfid.github.io
make test
ENDSSH
```

### Step 3: Makefile Integration

Add to project root `Makefile`:

```makefile
# AWS Testing Infrastructure
aws-up:
	@echo "Provisioning AWS test instance..."
	@./test_infra/aws/scripts/provision.sh

aws-ssh:
	@./test_infra/aws/scripts/connect.sh

aws-down:
	@echo "Destroying AWS test instance..."
	@./test_infra/aws/scripts/teardown.sh

aws-test:
	@echo "Running tests on AWS instance..."
	@./test_infra/aws/scripts/test_remote.sh

aws-status:
	@cd test_infra/aws/terraform && terraform show -json | jq -r '.values.root_module.resources[] | select(.type=="aws_instance") | "Instance: \(.values.id)\nPublic IP: \(.values.public_ip)\nState: \(.values.instance_state)"'
```

### Step 4: Git Configuration

Update `.gitignore`:

```
# Terraform
test_infra/aws/terraform/.terraform/
test_infra/aws/terraform/.terraform.lock.hcl
test_infra/aws/terraform/terraform.tfstate
test_infra/aws/terraform/terraform.tfstate.backup
test_infra/aws/terraform/terraform.tfvars
```

### Step 5: Documentation Updates

Update `test_infra/aws/README.md` to reference new IaC workflow.

## Testing the Implementation

### Initial Setup (One-Time)

```bash
# 1. Create terraform.tfvars
cd test_infra/aws/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your SSH key paths

# 2. Initialize Terraform
terraform init

# 3. Validate configuration
terraform validate
```

### First Provision

```bash
# From project root
make aws-up

# Expected output:
# - Terraform creates resources
# - Instance boots and runs user-data
# - Outputs SSH command
# - Time: ~90 seconds
```

### Verify Setup

```bash
make aws-ssh
# Should connect automatically

# On instance:
cd brfid.github.io
docker --version
docker compose version
git status
make check_env

# Exit
exit
```

### Test Lifecycle

```bash
# Full cycle
make aws-up      # Provision
make aws-ssh     # Connect and debug
make aws-down    # Destroy

# Remote test
make aws-up
make aws-test    # Runs tests without SSH
make aws-down
```

## Rollout Plan

### Phase 1: Core Infrastructure
- [ ] Create Terraform files (main.tf, variables.tf, outputs.tf)
- [ ] Create user-data.sh
- [ ] Create terraform.tfvars from example
- [ ] Test: terraform init, validate, plan
- [ ] Test: terraform apply (create instance)
- [ ] Verify: SSH works, Docker installed, repo cloned
- [ ] Test: terraform destroy
- [ ] Commit Terraform configuration

### Phase 2: Helper Scripts
- [ ] Create provision.sh, connect.sh, teardown.sh
- [ ] Make scripts executable
- [ ] Test each script individually
- [ ] Commit scripts

### Phase 3: Makefile Integration
- [ ] Add aws-* targets to Makefile
- [ ] Test make aws-up, aws-ssh, aws-down
- [ ] Verify workflow end-to-end
- [ ] Commit Makefile changes

### Phase 4: Documentation
- [ ] Update aws/README.md with IaC workflow
- [ ] Add troubleshooting section
- [ ] Create usage examples
- [ ] Update MEMORY.md
- [ ] Commit documentation

### Phase 5: Polish
- [ ] Add .gitignore entries
- [ ] Test from clean clone
- [ ] Verify costs in AWS console
- [ ] Document common issues
- [ ] Final commit

## Estimated Time

- Phase 1: 30 minutes
- Phase 2: 15 minutes
- Phase 3: 10 minutes
- Phase 4: 15 minutes
- Phase 5: 15 minutes

**Total**: ~1.5 hours

## Success Criteria

Implementation is complete when:
- [ ] `make aws-up` provisions instance in <2 minutes
- [ ] Instance has Docker, repo cloned, on correct branch
- [ ] `make aws-ssh` connects without manual steps
- [ ] `make aws-down` destroys all resources cleanly
- [ ] No Terraform state committed to git
- [ ] Documentation is complete and accurate
- [ ] Works from fresh clone of repo
- [ ] Cost verified at <$1 for test run

## Troubleshooting Guide

### Terraform Issues

**Issue**: `terraform init` fails
- Check AWS credentials: `aws sts get-caller-identity`
- Verify Terraform installed: `terraform version`

**Issue**: `terraform apply` fails with permission error
- Check IAM permissions for EC2, VPC, SecurityGroups
- Try different region in terraform.tfvars

**Issue**: Instance creation times out
- Check AWS service health dashboard
- Try different availability zone
- Increase timeout in main.tf provisioner

### SSH Issues

**Issue**: Can't SSH to instance
- Wait 30 more seconds (user-data still running)
- Check security group allows your IP: `curl ifconfig.me`
- Verify key permissions: `chmod 600 ~/.ssh/id_rsa`

**Issue**: "Permission denied (publickey)"
- Verify ssh_private_key_path in terraform.tfvars
- Check key matches: `ssh-keygen -y -f ~/.ssh/id_rsa`

### Cost Issues

**Issue**: Unexpected AWS charges
- Check for orphaned resources: `terraform state list`
- Verify EBS deletion: `aws ec2 describe-volumes`
- Ensure instances terminated: `aws ec2 describe-instances`

## Next Steps After Implementation

1. Use infrastructure to debug current IMP build failure
2. Document findings in MEMORY.md
3. Consider Phase 3 enhancements:
   - Auto-shutdown CloudWatch alarm
   - S3 artifact storage
   - GitHub Actions integration
