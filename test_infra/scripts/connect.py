#!/usr/bin/env python3
"""Connect to ARPANET test instance via SSH."""

import json
import subprocess
import sys


def get_stack_outputs():
    """Get CloudFormation stack outputs.

    Returns:
        Dictionary of stack outputs.
    """
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
