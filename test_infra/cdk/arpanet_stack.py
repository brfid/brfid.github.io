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
        logs_volume_size = context.get("logs_volume_size", 20)
        persist_logs_volume = context.get("persist_logs_volume", True)
        logs_retention_days = context.get("logs_retention_days", 14)
        ssh_public_key_path = os.path.expanduser(context["ssh_public_key_path"])
        allowed_ssh_cidrs = context.get("allowed_ssh_cidrs", ["0.0.0.0/0"])
        git_repo = context.get("git_repo", "https://github.com/brfid/brfid.github.io.git")
        git_branch = context.get("git_branch", "main")
        logs_volume_enabled = bool(logs_volume_size and logs_volume_size > 0)

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
        user_data_content = user_data_content.replace(
            "${logs_volume_enabled}",
            "true" if logs_volume_enabled else "false",
        )
        user_data_content = user_data_content.replace(
            "${logs_retention_days}",
            str(logs_retention_days),
        )

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(user_data_content)

        block_devices = [
            ec2.BlockDevice(
                device_name="/dev/sda1",
                volume=ec2.BlockDeviceVolume.ebs(
                    volume_size=root_volume_size,
                    volume_type=ec2.EbsDeviceVolumeType.GP3,
                    delete_on_termination=True,
                    encrypted=True,
                )
            )
        ]

        if logs_volume_enabled:
            block_devices.append(
                ec2.BlockDevice(
                    device_name="/dev/sdf",  # Appears as /dev/nvme* on newer instances
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=logs_volume_size,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=not persist_logs_volume,
                        encrypted=True,
                    )
                )
            )

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
            block_devices=block_devices,
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
