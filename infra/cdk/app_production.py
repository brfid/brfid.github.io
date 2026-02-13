#!/usr/bin/env python3
"""
ARPANET Production Infrastructure CDK App

Deploy with:
  cd infra/cdk
  source ../../.venv/bin/activate
  cdk deploy -a "python3 app_production.py" ArpanetProductionStack

Destroy with:
  cdk destroy -a "python3 app_production.py" ArpanetProductionStack --force
"""

import aws_cdk as cdk
from arpanet_production_stack import ArpanetProductionStack

app = cdk.App()

ArpanetProductionStack(
    app,
    "ArpanetProductionStack",
    description="ARPANET Production: 2x t3.micro (VAX + PDP-11) with shared EFS logging",
    env=cdk.Environment(
        account="972626128180",
        region="us-east-1",
    ),
)

app.synth()
