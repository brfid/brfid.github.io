#!/usr/bin/env python3
"""
ARPANET Production Infrastructure
Two-machine permanent setup with shared EFS logging

Machines:
  - VAX/BSD (Primary host)
  - PDP-11/BSD (Secondary host)

Storage:
  - Shared EFS volume for logs (~$0.73/month with IA tier)
  - Small root volumes (8GB gp3)
  - S3 bucket for long-term log archival (optional)

Total Cost: ~$17.90/month
  - 2x t3.micro: $15.00/month
  - 2x 8GB root: $1.28/month
  - EFS logs: ~$0.73/month
  - S3: negligible
"""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_s3 as s3,
    aws_iam as iam,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class ArpanetProductionStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =====================================================================
        # VPC - Use default VPC
        # =====================================================================
        vpc = ec2.Vpc.from_lookup(self, "VPC", is_default=True)

        # =====================================================================
        # Security Group - Allow SSH and inter-host communication
        # =====================================================================
        security_group = ec2.SecurityGroup(
            self,
            "ArpanetSG",
            vpc=vpc,
            description="ARPANET production hosts security group",
            allow_all_outbound=True,
        )

        # SSH access
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "Allow SSH access",
        )

        # Allow all traffic between ARPANET hosts
        security_group.add_ingress_rule(
            security_group,
            ec2.Port.all_traffic(),
            "Allow inter-host communication",
        )

        # =====================================================================
        # EFS - Shared log storage with Infrequent Access tier
        # =====================================================================
        file_system = efs.FileSystem(
            self,
            "ArpanetLogs",
            vpc=vpc,
            encrypted=True,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_7_DAYS,  # Move to IA after 7 days
            out_of_infrequent_access_policy=efs.OutOfInfrequentAccessPolicy.AFTER_1_ACCESS,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            removal_policy=RemovalPolicy.RETAIN,  # Keep logs if stack deleted
            enable_automatic_backups=True,  # Daily backups
        )

        # Allow NFS access from security group
        file_system.connections.allow_default_port_from(
            security_group,
            "Allow NFS from ARPANET hosts",
        )

        # =====================================================================
        # S3 - Optional long-term log archival
        # =====================================================================
        log_archive_bucket = s3.Bucket(
            self,
            "ArpanetLogArchive",
            bucket_name=f"arpanet-logs-{self.account}",
            versioned=False,
            encryption=s3.BucketEncryption.S3_MANAGED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                            transition_after=Duration.days(30),
                        ),
                    ],
                ),
            ],
            removal_policy=RemovalPolicy.RETAIN,  # Keep archives if stack deleted
        )

        # =====================================================================
        # IAM Role - Allow instances to write to S3 and access EFS
        # =====================================================================
        instance_role = iam.Role(
            self,
            "ArpanetInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonSSMManagedInstanceCore"  # For Session Manager access
                ),
            ],
        )

        # Grant S3 write access for log archival
        log_archive_bucket.grant_write(instance_role)

        # =====================================================================
        # User Data - Mount EFS and configure logging
        # =====================================================================
        user_data_script = ec2.UserData.for_linux()
        user_data_script.add_commands(
            "#!/bin/bash",
            "set -ex",
            "",
            "# Update system",
            "apt-get update -qq",
            "apt-get upgrade -y -qq",
            "",
            "# Install dependencies",
            "apt-get install -y -qq \\",
            "  docker.io \\",
            "  docker-compose \\",
            "  nfs-common \\",
            "  awscli \\",
            "  git \\",
            "  python3-pip",
            "",
            "# Enable Docker",
            "systemctl enable docker",
            "systemctl start docker",
            "usermod -aG docker ubuntu",
            "",
            "# Install EFS mount helper FIRST (before mounting)",
            "git clone https://github.com/aws/efs-utils /tmp/efs-utils",
            "cd /tmp/efs-utils",
            "bash ./build-deb.sh",
            "apt-get install -y ./build/amazon-efs-utils*deb",
            "",
            "# Create EFS mount point",
            "mkdir -p /mnt/arpanet-logs",
            "",
            "# Mount EFS (now that efs-utils is installed)",
            f"echo '{file_system.file_system_id}:/ /mnt/arpanet-logs efs _netdev,tls,iam 0 0' >> /etc/fstab",
            "mount -a -t efs defaults",
            "",
            "# Create log directories",
            "mkdir -p /mnt/arpanet-logs/vax",
            "mkdir -p /mnt/arpanet-logs/pdp11",
            "mkdir -p /mnt/arpanet-logs/shared",
            "mkdir -p /mnt/arpanet-logs/builds",
            "chown -R ubuntu:ubuntu /mnt/arpanet-logs",
            "",
            "# Clone repository",
            "cd /home/ubuntu",
            "git clone https://github.com/brfid/brfid.github.io.git",
            "chown -R ubuntu:ubuntu brfid.github.io",
            "",
            "# Setup S3 sync cron (daily at 2 AM)",
            "cat > /etc/cron.daily/arpanet-log-sync <<'EOF'",
            "#!/bin/bash",
            f"aws s3 sync /mnt/arpanet-logs/ s3://{log_archive_bucket.bucket_name}/ \\",
            "  --exclude '*.tmp' \\",
            "  --exclude '*.lock' \\",
            "  --storage-class GLACIER_IR",
            "EOF",
            "chmod +x /etc/cron.daily/arpanet-log-sync",
            "",
            "# Signal completion",
            "echo 'ARPANET setup complete' > /tmp/setup-complete",
        )

        # =====================================================================
        # EC2 Instance - VAX Host
        # =====================================================================
        vax_instance = ec2.Instance(
            self,
            "VaxHost",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO,
            ),
            machine_image=ec2.MachineImage.from_ssm_parameter(
                "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=security_group,
            role=instance_role,
            key_name="arpanet-temp",  # SSH access
            user_data=user_data_script,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=8,  # 8GB root
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=False,  # Retain on instance termination
                    ),
                ),
            ],
        )

        # =====================================================================
        # EC2 Instance - PDP-11 Host
        # =====================================================================
        pdp11_instance = ec2.Instance(
            self,
            "Pdp11Host",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO,
            ),
            machine_image=ec2.MachineImage.from_ssm_parameter(
                "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=security_group,
            role=instance_role,
            key_name="arpanet-temp",  # SSH access
            user_data=user_data_script,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/sda1",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=8,  # 8GB root
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=False,  # Retain on instance termination
                    ),
                ),
            ],
        )

        # =====================================================================
        # Outputs
        # =====================================================================
        CfnOutput(
            self,
            "VaxPublicIP",
            value=vax_instance.instance_public_ip,
            description="VAX host public IP",
        )

        CfnOutput(
            self,
            "Pdp11PublicIP",
            value=pdp11_instance.instance_public_ip,
            description="PDP-11 host public IP",
        )

        CfnOutput(
            self,
            "VaxInstanceId",
            value=vax_instance.instance_id,
            description="VAX instance ID",
        )

        CfnOutput(
            self,
            "Pdp11InstanceId",
            value=pdp11_instance.instance_id,
            description="PDP-11 instance ID",
        )

        CfnOutput(
            self,
            "EfsFileSystemId",
            value=file_system.file_system_id,
            description="EFS file system ID",
        )

        CfnOutput(
            self,
            "LogArchiveBucket",
            value=log_archive_bucket.bucket_name,
            description="S3 log archive bucket",
        )

        CfnOutput(
            self,
            "LogsPath",
            value="/mnt/arpanet-logs",
            description="Shared logs mount point",
        )

        CfnOutput(
            self,
            "SSHCommandVax",
            value=f"ssh ubuntu@{vax_instance.instance_public_ip}",
            description="SSH command for VAX",
        )

        CfnOutput(
            self,
            "SSHCommandPdp11",
            value=f"ssh ubuntu@{pdp11_instance.instance_public_ip}",
            description="SSH command for PDP-11",
        )

        CfnOutput(
            self,
            "EstimatedMonthlyCost",
            value="$17.90",
            description="Estimated monthly cost (2x t3.micro + EFS + storage)",
        )
