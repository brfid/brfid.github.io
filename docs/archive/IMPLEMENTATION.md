# AWS Testing Infrastructure - CDK Implementation Plan

> **Archive notice (historical document)**
>
> This implementation plan documents an earlier migration stage and is retained
> for history. Path references to `test_infra/aws/...` are outdated.
>
> For current implementation and commands, use:
> - `test_infra/README.md`
> - `test_infra/cdk/`
> - `test_infra/scripts/`

Step-by-step plan to build ephemeral EC2 testing with AWS CDK in Python.

## Prerequisites

- AWS account with EC2 access
- AWS CLI configured with credentials (`aws configure`)
- Python 3.8+ installed
- Node.js installed (CDK CLI requirement)
- SSH key pair available

## Installation Steps

### 1. Install AWS CDK CLI

```bash
# Install CDK globally
npm install -g aws-cdk

# Verify installation
cdk --version
```

### 2. Bootstrap CDK (One-time per AWS account/region)

```bash
# Bootstrap creates S3 bucket for CDK assets
cdk bootstrap aws://ACCOUNT-ID/us-east-1

# Or let CDK auto-detect
cd test_infra/aws/cdk
cdk bootstrap
```

## Implementation Steps

### Step 1: CDK Application Files

Create the following files in `test_infra/aws/cdk/`:

#### 1.1 `requirements.txt` - Python Dependencies

```txt
aws-cdk-lib>=2.0.0
constructs>=10.0.0
boto3>=1.26.0
```

#### 1.2 `cdk.json` - CDK Configuration

```json
{
  "app": "python3 app.py",
  "watch": {
    "include": [
      "**"
    ],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "source.bat",
      "**/__init__.py",
      "**/__pycache__",
      "**/.pytest_cache"
    ]
  },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": [
      "aws"
    ],
    "@aws-cdk-containers/ecs-service-extensions:enableDefaultLogDriver": true,
    "@aws-cdk/aws-ec2:uniqueImdsv2TemplateName": true,
    "@aws-cdk/aws-ecs:arnFormatIncludesClusterName": true,
    "@aws-cdk/aws-iam:minimizePolicies": true,
    "@aws-cdk/core:validateSnapshotRemovalPolicy": true,
    "@aws-cdk/aws-codepipeline:crossAccountKeyAliasStackSafeResourceName": true,
    "@aws-cdk/aws-s3:createDefaultLoggingPolicy": true,
    "@aws-cdk/aws-sns-subscriptions:restrictSqsDescryption": true,
    "@aws-cdk/aws-apigateway:disableCloudWatchRole": true,
    "@aws-cdk/core:enablePartitionLiterals": true,
    "@aws-cdk/aws-events:eventsTargetQueueSameAccount": true,
    "@aws-cdk/aws-iam:standardizedServicePrincipals": true,
    "@aws-cdk/aws-ecs:disableExplicitDeploymentControllerForCircuitBreaker": true,
    "@aws-cdk/aws-iam:importedRoleStackSafeDefaultPolicyName": true,
    "@aws-cdk/aws-s3:serverAccessLogsUseBucketPolicy": true,
    "@aws-cdk/aws-route53-patters:useCertificate": true,
    "@aws-cdk/customresources:installLatestAwsSdkDefault": false,
    "@aws-cdk/aws-rds:databaseProxyUniqueResourceName": true,
    "@aws-cdk/aws-codedeploy:removeAlarmsFromDeploymentGroup": true,
    "@aws-cdk/aws-apigateway:authorizerChangeDeploymentLogicalId": true,
    "@aws-cdk/aws-ec2:launchTemplateDefaultUserData": true,
    "@aws-cdk/aws-secretsmanager:useAttachedSecretResourcePolicyForSecretTargetAttachments": true,
    "@aws-cdk/aws-redshift:columnId": true,
    "@aws-cdk/aws-stepfunctions-tasks:enableEmrServicePolicyV2": true,
    "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true,
    "@aws-cdk/aws-apigateway:requestValidatorUniqueId": true,
    "@aws-cdk/aws-kms:aliasNameRef": true,
    "@aws-cdk/aws-autoscaling:generateLaunchTemplateInsteadOfLaunchConfig": true,
    "@aws-cdk/core:includePrefixInUniqueNameGeneration": true,
    "@aws-cdk/aws-efs:denyAnonymousAccess": true,
    "@aws-cdk/aws-opensearchservice:enableOpensearchMultiAzWithStandby": true,
    "@aws-cdk/aws-lambda-nodejs:useLatestRuntimeVersion": true,
    "@aws-cdk/aws-efs:mountTargetOrderInsensitiveLogicalId": true,
    "@aws-cdk/aws-rds:auroraClusterChangeScopeOfInstanceParameterGroupWithEachParameters": true,
    "@aws-cdk/aws-appsync:useArnForSourceApiAssociationIdentifier": true,
    "@aws-cdk/aws-rds:preventRenderingDeprecatedCredentials": true,
    "@aws-cdk/aws-codepipeline-actions:useNewDefaultBranchForCodeCommitSource": true,
    "@aws-cdk/aws-cloudwatch-actions:changeLambdaPermissionLogicalIdForLambdaAction": true,
    "@aws-cdk/aws-codepipeline:crossAccountKeysDefaultValueToFalse": true,
    "@aws-cdk/aws-codepipeline:defaultPipelineTypeToV2": true,
    "@aws-cdk/aws-kms:reduceCrossAccountRegionPolicyScope": true,
    "@aws-cdk/aws-eks:nodegroupNameAttribute": true,
    "@aws-cdk/aws-ec2:ebsDefaultGp3Volume": true,
    "@aws-cdk/aws-ecs:removeDefaultDeploymentAlarm": true,
    "@aws-cdk/custom-resources:logApiResponseDataPropertyTrueDefault": false,
    "@aws-cdk/aws-s3:keepNotificationInImportedBucket": false
  }
}
```

#### 1.3 `cdk.context.json.example` - User Configuration Template

```json
{
  "ssh_public_key_path": "~/.ssh/id_rsa.pub",
  "ssh_private_key_path": "~/.ssh/id_rsa",
  "instance_type": "t3.medium",
  "root_volume_size": 30,
  "allowed_ssh_cidrs": ["0.0.0.0/0"],
  "git_repo": "https://github.com/brfid/brfid.github.io.git",
  "git_branch": "claude/arpanet-build-integration-uU9ZL",
  "aws_region": "us-east-1"
}
```

#### 1.4 `app.py` - CDK Entry Point

```python
#!/usr/bin/env python3
"""AWS CDK app for ARPANET testing infrastructure."""

import json
import os
from pathlib import Path

import aws_cdk as cdk

from arpanet_stack import ArpanetTestStack


def load_context():
    """Load context from cdk.context.json.

    Returns:
        Dictionary of context values.
    """
    context_file = Path(__file__).parent / "cdk.context.json"

    if not context_file.exists():
        raise FileNotFoundError(
            f"Context file not found: {context_file}\n"
            f"Copy cdk.context.json.example to cdk.context.json and customize"
        )

    with open(context_file) as f:
        return json.load(f)


app = cdk.App()

# Load user context
context = load_context()

# Create stack
ArpanetTestStack(
    app,
    "ArpanetTestStack",
    context=context,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=context.get("aws_region", "us-east-1")
    ),
    description="Ephemeral EC2 instance for ARPANET integration testing"
)

app.synth()
```

#### 1.5 `arpanet_stack.py` - Stack Definition

```python
"""ARPANET testing infrastructure stack."""

import os
from pathlib import Path

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput,
)
from constructs import Construct


class ArpanetTestStack(Stack):
    """Stack for ARPANET testing EC2 instance."""

    def __init__(self, scope: Construct, construct_id: str, context: dict, **kwargs) -> None:
        """Initialize the stack.

        Args:
            scope: CDK app scope.
            construct_id: Stack ID.
            context: User configuration from cdk.context.json.
            **kwargs: Additional stack arguments.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Get configuration from context
        instance_type = context.get("instance_type", "t3.medium")
        root_volume_size = context.get("root_volume_size", 30)
        ssh_public_key_path = os.path.expanduser(context["ssh_public_key_path"])
        allowed_ssh_cidrs = context.get("allowed_ssh_cidrs", ["0.0.0.0/0"])
        git_repo = context.get("git_repo", "https://github.com/brfid/brfid.github.io.git")
        git_branch = context.get("git_branch", "claude/arpanet-build-integration-uU9ZL")

        # Read SSH public key
        with open(ssh_public_key_path) as f:
            ssh_public_key = f.read().strip()

        # Use default VPC
        vpc = ec2.Vpc.from_lookup(self, "VPC", is_default=True)

        # Security group
        security_group = ec2.SecurityGroup(
            self,
            "ArpanetTestSG",
            vpc=vpc,
            description="Security group for ARPANET testing instance",
            allow_all_outbound=True,
        )

        # Allow SSH from specified CIDRs
        for cidr in allowed_ssh_cidrs:
            security_group.add_ingress_rule(
                ec2.Peer.ipv4(cidr),
                ec2.Port.tcp(22),
                "Allow SSH"
            )

        # SSH key pair
        key_pair = ec2.CfnKeyPair(
            self,
            "ArpanetTestKey",
            key_name="arpanet-test-key",
            public_key_material=ssh_public_key,
        )

        # User data script
        user_data_script = Path(__file__).parent / "user_data.sh"
        with open(user_data_script) as f:
            user_data_content = f.read()

        # Template user data with git repo and branch
        user_data_content = user_data_content.replace("${git_repo}", git_repo)
        user_data_content = user_data_content.replace("${git_branch}", git_branch)

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(user_data_content)

        # EC2 instance
        instance = ec2.Instance(
            self,
            "ArpanetTestInstance",
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ec2.MachineImage.from_ssm_parameter(
                "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
            ),
            vpc=vpc,
            security_group=security_group,
            key_name=key_pair.key_name,
            user_data=user_data,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=root_volume_size,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=True,
                        encrypted=True,
                    )
                )
            ],
        )

        # Outputs
        CfnOutput(
            self,
            "InstanceId",
            value=instance.instance_id,
            description="EC2 instance ID"
        )

        CfnOutput(
            self,
            "InstancePublicIP",
            value=instance.instance_public_ip,
            description="Public IP address"
        )

        CfnOutput(
            self,
            "SSHCommand",
            value=f"ssh -i {context['ssh_private_key_path']} ubuntu@{instance.instance_public_ip}",
            description="SSH connection command"
        )
```

#### 1.6 `user_data.sh` - Cloud-Init Script

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
curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
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

# Pre-pull VAX image to save time
echo "Pre-pulling VAX Docker image..."
su - ubuntu -c "docker pull jguillaumes/simh-vaxbsd@sha256:1bab805b25a793fd622c29d3e9b677b002cabbdc20d9c42afaeeed542cc42215"

echo "Setup complete at: $(date)"
echo "Instance ready for testing"
```

### Step 2: Python Helper Scripts

Create in `test_infra/aws/scripts/`:

#### 2.1 `provision.py`

```python
#!/usr/bin/env python3
"""Provision ARPANET test infrastructure using CDK."""

import subprocess
import sys
from pathlib import Path


def main():
    """Deploy CDK stack."""
    cdk_dir = Path(__file__).parent.parent / "cdk"

    print("=== Provisioning ARPANET Test Instance ===")
    print(f"CDK directory: {cdk_dir}")

    # Install dependencies
    print("\nInstalling Python dependencies...")
    subprocess.run(
        ["pip3", "install", "-q", "-r", "requirements.txt"],
        cwd=cdk_dir,
        check=True
    )

    # Deploy stack
    print("\nDeploying CDK stack...")
    result = subprocess.run(
        ["cdk", "deploy", "--require-approval", "never"],
        cwd=cdk_dir,
    )

    if result.returncode != 0:
        print("\n❌ Deployment failed")
        sys.exit(1)

    print("\n✅ Instance provisioned successfully")
    print("\nUse 'make aws-ssh' to connect")


if __name__ == "__main__":
    main()
```

#### 2.2 `connect.py`

```python
#!/usr/bin/env python3
"""Connect to ARPANET test instance via SSH."""

import json
import subprocess
import sys
from pathlib import Path


def get_stack_outputs():
    """Get CloudFormation stack outputs.

    Returns:
        Dictionary of stack outputs.
    """
    cdk_dir = Path(__file__).parent.parent / "cdk"

    result = subprocess.run(
        ["aws", "cloudformation", "describe-stacks", "--stack-name", "ArpanetTestStack"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("❌ Error: No active instance (run 'make aws-up' first)")
        sys.exit(1)

    stacks = json.loads(result.stdout)
    if not stacks.get("Stacks"):
        print("❌ Error: Stack not found")
        sys.exit(1)

    outputs = {}
    for output in stacks["Stacks"][0].get("Outputs", []):
        outputs[output["OutputKey"]] = output["OutputValue"]

    return outputs


def main():
    """Connect to instance via SSH."""
    print("Connecting to ARPANET test instance...")

    outputs = get_stack_outputs()
    ssh_command = outputs.get("SSHCommand")

    if not ssh_command:
        print("❌ Error: Could not get SSH command from stack outputs")
        sys.exit(1)

    # Execute SSH command
    subprocess.run(ssh_command, shell=True)


if __name__ == "__main__":
    main()
```

#### 2.3 `destroy.py`

```python
#!/usr/bin/env python3
"""Destroy ARPANET test infrastructure."""

import subprocess
import sys
from pathlib import Path


def main():
    """Destroy CDK stack."""
    cdk_dir = Path(__file__).parent.parent / "cdk"

    print("=== Destroying ARPANET Test Instance ===")

    result = subprocess.run(
        ["cdk", "destroy", "--force"],
        cwd=cdk_dir,
    )

    if result.returncode != 0:
        print("\n❌ Destruction failed")
        sys.exit(1)

    print("\n✅ Instance destroyed successfully")


if __name__ == "__main__":
    main()
```

#### 2.4 `status.py`

```python
#!/usr/bin/env python3
"""Check status of ARPANET test instance."""

import json
import subprocess
import sys


def main():
    """Get instance status from CloudFormation."""
    result = subprocess.run(
        ["aws", "cloudformation", "describe-stacks", "--stack-name", "ArpanetTestStack"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("No active instance")
        sys.exit(0)

    stacks = json.loads(result.stdout)
    if not stacks.get("Stacks"):
        print("No active instance")
        sys.exit(0)

    stack = stacks["Stacks"][0]

    print(f"Stack: {stack['StackName']}")
    print(f"Status: {stack['StackStatus']}")
    print(f"Created: {stack['CreationTime']}")

    print("\nOutputs:")
    for output in stack.get("Outputs", []):
        print(f"  {output['OutputKey']}: {output['OutputValue']}")


if __name__ == "__main__":
    main()
```

### Step 3: Update Makefile

Makefile targets already configured for Python scripts (`.sh` → `.py`):

```makefile
# AWS Infrastructure
aws-up:
	@echo "Provisioning AWS test instance..."
	@./test_infra/aws/scripts/provision.py

aws-ssh:
	@./test_infra/aws/scripts/connect.py

aws-down:
	@echo "Destroying AWS test instance..."
	@./test_infra/aws/scripts/destroy.py

aws-status:
	@./test_infra/aws/scripts/status.py
```

### Step 4: Update .gitignore

```gitignore
# CDK
test_infra/aws/cdk/cdk.out/
test_infra/aws/cdk/cdk.context.json
test_infra/aws/cdk/.venv/
test_infra/aws/cdk/__pycache__/
```

## Testing the Implementation

### Initial Setup (One-Time)

```bash
# 1. Install CDK CLI
npm install -g aws-cdk

# 2. Create context file
cd test_infra/aws/cdk
cp cdk.context.json.example cdk.context.json
# Edit cdk.context.json with your SSH key paths

# 3. Install Python dependencies
pip3 install -r requirements.txt

# 4. Bootstrap CDK (if not done already)
cdk bootstrap

# 5. Validate CDK app
cdk synth
```

### First Provision

```bash
# From project root
make aws-up

# Expected output:
# - CDK synthesizes CloudFormation template
# - CloudFormation creates resources
# - Instance boots and runs user-data
# - Outputs SSH command
# - Time: ~2-3 minutes
```

### Verify Setup

```bash
# Check status
make aws-status

# Connect
make aws-ssh

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
make aws-up      # Provision (~2 min)
make aws-status  # Check status
make aws-ssh     # Connect and debug
make aws-down    # Destroy (~1 min)
```

## Rollout Plan

### Phase 1: CDK Core (~30 min)
- [ ] Install CDK CLI
- [ ] Create cdk/ directory structure
- [ ] Create requirements.txt
- [ ] Create cdk.json
- [ ] Create cdk.context.json from example
- [ ] Create app.py
- [ ] Create arpanet_stack.py
- [ ] Create user_data.sh
- [ ] Test: `cdk synth`
- [ ] Bootstrap: `cdk bootstrap`
- [ ] Deploy: `cdk deploy`
- [ ] Verify: SSH works, Docker installed, repo cloned
- [ ] Destroy: `cdk destroy`

### Phase 2: Helper Scripts (~20 min)
- [ ] Create provision.py
- [ ] Create connect.py
- [ ] Create destroy.py
- [ ] Create status.py
- [ ] Make scripts executable
- [ ] Test each script
- [ ] Update Makefile to use .py scripts

### Phase 3: Integration (~15 min)
- [ ] Test make aws-up
- [ ] Test make aws-ssh
- [ ] Test make aws-status
- [ ] Test make aws-down
- [ ] Verify full workflow

### Phase 4: Documentation (~10 min)
- [ ] Update aws/README.md
- [ ] Update MEMORY.md
- [ ] Update .gitignore
- [ ] Commit all changes

### Phase 5: Validation (~10 min)
- [ ] Test from clean state
- [ ] Verify costs in AWS console
- [ ] Document any issues
- [ ] Final commit

## Estimated Time

- Phase 1: 30 minutes
- Phase 2: 20 minutes
- Phase 3: 15 minutes
- Phase 4: 10 minutes
- Phase 5: 10 minutes

**Total**: ~1.5 hours

## Success Criteria

- [ ] `make aws-up` provisions instance in <3 minutes
- [ ] Instance has Docker, repo cloned, on correct branch
- [ ] `make aws-ssh` connects without manual steps
- [ ] `make aws-down` destroys all resources cleanly
- [ ] No CDK context committed to git
- [ ] Documentation is complete and accurate
- [ ] All code is Python (CDK + helper scripts)
- [ ] Cost verified at <$1 for 2-hour test session

## Troubleshooting

### CDK Issues

**Issue**: `cdk` command not found
- Install: `npm install -g aws-cdk`
- Verify: `cdk --version`

**Issue**: CDK bootstrap fails
- Check AWS credentials: `aws sts get-caller-identity`
- Verify permissions for CloudFormation, S3, IAM

**Issue**: `cdk synth` fails
- Check Python syntax in app.py, arpanet_stack.py
- Verify cdk.context.json exists and is valid JSON
- Check SSH key path is correct

### SSH Issues

**Issue**: Can't SSH to instance
- Wait 2-3 minutes for user-data to complete
- Check security group allows your IP
- Verify key permissions: `chmod 600 ~/.ssh/id_rsa`

### CloudFormation Issues

**Issue**: Stack creation fails
- Check CloudFormation console for detailed errors
- View Events tab for failure reason
- Check CloudWatch Logs for user-data output

## Next Steps

1. Use infrastructure to debug ARPANET IMP build failure
2. Document findings in MEMORY.md
3. Consider Phase 2 enhancements:
   - Auto-shutdown Lambda
   - S3 artifact storage
   - CloudWatch dashboards
