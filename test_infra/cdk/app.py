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
