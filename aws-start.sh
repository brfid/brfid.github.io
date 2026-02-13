#!/bin/bash
# Start AWS ARPANET Production Instances
# This DOES NOT delete any data - EFS and EBS volumes remain intact

set -e

echo "🚀 Starting ARPANET Production Instances..."
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

# Start instances
echo "Starting instances..."
aws ec2 start-instances --instance-ids $VAX_ID $PDP11_ID

echo ""
echo "⏳ Waiting for instances to start..."
aws ec2 wait instance-running --instance-ids $VAX_ID $PDP11_ID

echo ""
echo "✅ Instances started successfully!"
echo ""

# Get new IP addresses (they change after stop/start)
VAX_IP=$(aws ec2 describe-instances \
  --instance-ids $VAX_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
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
