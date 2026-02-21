#!/usr/bin/env python3
"""edcloud lifecycle helper backed by AWS CLI.

This script centralizes logic that was previously duplicated across:
  - aws-start.sh
  - aws-stop.sh
  - aws-status.sh
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Runtime configuration resolved from environment variables."""

    name_tag: str
    manager_tag: str
    manager_value: str
    tailscale_host: str
    explicit_instance_id: str | None


def load_config() -> Config:
    """Load environment-backed configuration."""
    explicit = os.getenv("EDCLOUD_INSTANCE_ID")
    return Config(
        name_tag=os.getenv("EDCLOUD_NAME_TAG", "edcloud"),
        manager_tag=os.getenv("EDCLOUD_MANAGER_TAG", "edcloud:managed"),
        manager_value=os.getenv("EDCLOUD_MANAGER_VALUE", "true"),
        tailscale_host=os.getenv("EDCLOUD_HOSTNAME", "edcloud"),
        explicit_instance_id=explicit if explicit else None,
    )


def run_aws(args: list[str], *, tolerate_failure: bool = False) -> str:
    """Run an AWS CLI command and return stdout.

    Args:
        args: CLI arguments excluding the leading ``aws`` token.
        tolerate_failure: Whether non-zero exit status should be tolerated.

    Returns:
        Captured stdout text with surrounding whitespace stripped.

    Raises:
        RuntimeError: If command fails and failure is not tolerated.
    """
    proc = subprocess.run(
        ["aws", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 and not tolerate_failure:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        detail = stderr or stdout or "unknown aws cli error"
        raise RuntimeError(f"aws {' '.join(args)} failed: {detail}")
    return proc.stdout.strip()


def resolve_instance_id(cfg: Config) -> str:
    """Resolve the target instance ID from env override or tags."""
    if cfg.explicit_instance_id:
        return cfg.explicit_instance_id

    instance_id = run_aws(
        [
            "ec2",
            "describe-instances",
            "--filters",
            f"Name=tag:{cfg.manager_tag},Values={cfg.manager_value}",
            f"Name=tag:Name,Values={cfg.name_tag}",
            "Name=instance-state-name,Values=pending,running,stopping,stopped",
            "--query",
            "Reservations[].Instances[] | sort_by(@, &LaunchTime)[-1].InstanceId",
            "--output",
            "text",
        ]
    )

    if not instance_id or instance_id == "None":
        raise RuntimeError(
            "No edcloud-managed instance found. "
            "Set EDCLOUD_INSTANCE_ID or provision edcloud first."
        )
    return instance_id


def get_instance_field(instance_id: str, field_query: str) -> str:
    """Fetch a single field from describe-instances by JMESPath query."""
    return run_aws(
        [
            "ec2",
            "describe-instances",
            "--instance-ids",
            instance_id,
            "--query",
            field_query,
            "--output",
            "text",
        ]
    )


def cmd_start(cfg: Config) -> int:
    """Start edcloud instance and wait until running."""
    instance_id = resolve_instance_id(cfg)
    state = get_instance_field(instance_id, "Reservations[0].Instances[0].State.Name")

    if state == "running":
        print(f"Instance already running: {instance_id}")
    else:
        print(f"Starting instance: {instance_id}")
        run_aws(["ec2", "start-instances", "--instance-ids", instance_id])
        print("Waiting for running state...")
        run_aws(["ec2", "wait", "instance-running", "--instance-ids", instance_id])

    public_ip = get_instance_field(instance_id, "Reservations[0].Instances[0].PublicIpAddress")

    print("Instance is running.")
    if public_ip and public_ip != "None":
        print(f"Public IP: {public_ip}")
        print(f"SSH (public): ssh ubuntu@{public_ip}")
    print(f"Tailscale host: {cfg.tailscale_host}")
    return 0


def cmd_stop(cfg: Config) -> int:
    """Stop edcloud instance and wait until stopped."""
    instance_id = resolve_instance_id(cfg)
    state = get_instance_field(instance_id, "Reservations[0].Instances[0].State.Name")

    if state == "stopped":
        print(f"Instance already stopped: {instance_id}")
        return 0
    if state == "stopping":
        print(f"Instance already stopping: {instance_id}")
        run_aws(["ec2", "wait", "instance-stopped", "--instance-ids", instance_id])
        print("Instance is stopped.")
        return 0

    print(f"Stopping instance: {instance_id}")
    run_aws(["ec2", "stop-instances", "--instance-ids", instance_id])
    run_aws(["ec2", "wait", "instance-stopped", "--instance-ids", instance_id])
    print("Instance is stopped.")
    return 0


def cmd_status(cfg: Config) -> int:
    """Show edcloud instance status and estimated costs."""
    instance_id = resolve_instance_id(cfg)
    state = get_instance_field(instance_id, "Reservations[0].Instances[0].State.Name")
    instance_type = get_instance_field(instance_id, "Reservations[0].Instances[0].InstanceType")
    public_ip = get_instance_field(instance_id, "Reservations[0].Instances[0].PublicIpAddress")
    launch_time = get_instance_field(instance_id, "Reservations[0].Instances[0].LaunchTime")

    print(f"Instance:  {instance_id}")
    print(f"State:     {state}")
    print(f"Type:      {instance_type}")
    if public_ip and public_ip != "None":
        print(f"Public IP: {public_ip}")
    print(f"Tailscale: {cfg.tailscale_host} (connect from your tailnet)")
    if launch_time and launch_time != "None":
        print(f"Launched:  {launch_time}")

    volumes = run_aws(
        [
            "ec2",
            "describe-volumes",
            "--filters",
            f"Name=attachment.instance-id,Values={instance_id}",
            "--query",
            "Volumes[].[VolumeId,Size,VolumeType,State]",
            "--output",
            "text",
        ],
        tolerate_failure=True,
    )
    if volumes:
        for line in volumes.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            vol_id, size_gb, vol_type, vol_state = parts[:4]
            print(f"Volume:    {vol_id}  {size_gb}GB {vol_type}  ({vol_state})")

    print()
    print("Estimated monthly cost (Assumes 4hrs/day runtime):")
    print("  Compute: $4.51")
    print("  Storage: $6.40")
    print("  Total:   $10.91")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command-line parser."""
    parser = argparse.ArgumentParser(prog="edcloud-lifecycle")
    parser.add_argument("command", choices=["start", "stop", "status"])
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = load_config()

    try:
        if args.command == "start":
            return cmd_start(cfg)
        if args.command == "stop":
            return cmd_stop(cfg)
        return cmd_status(cfg)
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
