#!/bin/bash
# Stop AWS ARPANET Production Instances
# This DOES NOT delete any data - EFS and EBS volumes remain intact
# Saves ~$15/month while stopped

set -e

echo "🛑 Stopping ARPANET Production Instances..."
echo ""

# Get instance IDs from CloudFormation stack
VAX_ID=$(aws cloudformation describe-stacks \
  --stack-name ArpanetProductionStack \
  --query 'Stacks[0].Outputs[?OutputKey==`VaxInstanceId`].OutputValue' \
  --output text)

PDP11_ID=$(aws cloudformation describe-stacks \
  --stack-name ArpanetProductionStack \
  --query 'Stacks[0].Outputs[?OutputKey==`Pdp11InstanceId`].OutputValue' \
  --output text)

echo "VAX Instance:    $VAX_ID"
echo "PDP-11 Instance: $PDP11_ID"
echo ""

# Stop instances
echo "Stopping instances..."
aws ec2 stop-instances --instance-ids $VAX_ID $PDP11_ID

echo ""
echo "⏳ Waiting for instances to stop..."
aws ec2 wait instance-stopped --instance-ids $VAX_ID $PDP11_ID

echo ""
echo "✅ Instances stopped successfully!"
echo ""
echo "💾 All data preserved:"
echo "   - EFS shared logs at fs-03cd0abbb728b4ad8"
echo "   - VAX root volume (8GB)"
echo "   - PDP-11 root volume (8GB)"
echo ""
echo "💰 Cost while stopped: ~\$2/month (storage only)"
echo "💰 Savings: ~\$15/month (no compute charges)"
echo ""
echo "To restart: ./aws-start.sh"
