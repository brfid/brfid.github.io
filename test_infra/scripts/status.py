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
