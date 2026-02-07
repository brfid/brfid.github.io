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
