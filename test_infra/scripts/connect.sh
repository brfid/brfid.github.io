#!/bin/bash
set -e

cd "$(dirname "$0")/../terraform"

if [ ! -f terraform.tfstate ]; then
    echo "Error: No active instance (run 'make aws-up' first)"
    exit 1
fi

SSH_CMD=$(terraform output -raw ssh_command 2>/dev/null)

if [ -z "$SSH_CMD" ]; then
    echo "Error: Could not get SSH command from Terraform"
    exit 1
fi

echo "Connecting to ARPANET test instance..."
eval $SSH_CMD
