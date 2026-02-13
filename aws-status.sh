#!/bin/bash
# Check AWS ARPANET Production Instance Status
# Shows current state without making any changes

set -e

echo "📊 ARPANET Production Instance Status"
echo "======================================"
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

# Get instance details
VAX_STATE=$(aws ec2 describe-instances \
  --instance-ids $VAX_ID \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

PDP11_STATE=$(aws ec2 describe-instances \
  --instance-ids $PDP11_ID \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

VAX_IP=$(aws ec2 describe-instances \
  --instance-ids $VAX_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

PDP11_IP=$(aws ec2 describe-instances \
  --instance-ids $PDP11_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "VAX Instance ($VAX_ID):"
echo "  State: $VAX_STATE"
if [ "$VAX_IP" != "None" ]; then
    echo "  IP:    $VAX_IP"
fi
echo ""

echo "PDP-11 Instance ($PDP11_ID):"
echo "  State: $PDP11_STATE"
if [ "$PDP11_IP" != "None" ]; then
    echo "  IP:    $PDP11_IP"
fi
echo ""

# Get EFS details
EFS_ID=$(aws cloudformation describe-stacks \
  --stack-name ArpanetProductionStack \
  --query 'Stacks[0].Outputs[?OutputKey==`EfsFileSystemId`].OutputValue' \
  --output text)

echo "Shared Storage (EFS $EFS_ID):"
echo "  Mount: /mnt/arpanet-logs/"
echo "  Status: Available (persists regardless of instance state)"
echo ""

# Show cost estimate
if [ "$VAX_STATE" == "running" ] && [ "$PDP11_STATE" == "running" ]; then
    echo "💰 Current Cost: ~\$0.60/day (~\$17.90/month)"
    echo ""
    echo "Commands:"
    echo "  ./aws-stop.sh  - Stop instances (saves ~\$15/month)"
    if [ "$VAX_IP" != "None" ]; then
        echo ""
        echo "SSH Access:"
        echo "  ssh -i ~/.ssh/arpanet-temp.pem ubuntu@$VAX_IP"
        echo "  ssh -i ~/.ssh/arpanet-temp.pem ubuntu@$PDP11_IP"
    fi
elif [ "$VAX_STATE" == "stopped" ] && [ "$PDP11_STATE" == "stopped" ]; then
    echo "💰 Current Cost: ~\$2/month (storage only)"
    echo ""
    echo "Commands:"
    echo "  ./aws-start.sh - Start instances (resume work)"
else
    echo "⚠️  Mixed state - some instances may be starting/stopping"
fi
