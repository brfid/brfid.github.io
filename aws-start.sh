#!/bin/bash
# Start edcloud build host
# Note: This script is for local convenience. GitHub Actions uses 'edcloud up' directly.

set -e

cd "$(dirname "$0")/../edcloud" 2>/dev/null || {
  echo "Error: edcloud not found. Expected at ../edcloud/"
  echo "This project now uses edcloud for distributed vintage builds."
  exit 1
}

source .venv/bin/activate
exec edcloud up \
  --output text)

PDP11_IP=$(aws ec2 describe-instances \
  --instance-ids $PDP11_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "📍 New IP Addresses:"
echo "   VAX:    $VAX_IP"
echo "   PDP-11: $PDP11_IP"
echo ""
echo "SSH Access:"
echo "   ssh -i ~/.ssh/arpanet-temp.pem ubuntu@$VAX_IP"
echo "   ssh -i ~/.ssh/arpanet-temp.pem ubuntu@$PDP11_IP"
echo ""
echo "Console Access:"
echo "   telnet $VAX_IP 2323    (VAX)"
echo "   telnet $PDP11_IP 2327  (PDP-11)"
echo ""
echo "💾 All data preserved (EFS + EBS volumes intact)"
echo "💰 Now costing ~\$0.60/day (~\$17.90/month)"
