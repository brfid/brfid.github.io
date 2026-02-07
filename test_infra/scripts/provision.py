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
