#!/bin/bash
set -e

cd "$(dirname "$0")/../terraform"

echo "=== Provisioning ARPANET Test Instance ==="
terraform init
terraform apply -auto-approve

echo ""
echo "=== Instance Ready ==="
terraform output ssh_command
