#!/bin/bash
# Check edcloud build host status
# Note: This script is for local convenience.

set -e

cd "$(dirname "$0")/../edcloud" 2>/dev/null || {
  echo "Error: edcloud not found. Expected at ../edcloud/"
  echo "This project now uses edcloud for distributed vintage builds."
  exit 1
}

source .venv/bin/activate
exec edcloud status

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
