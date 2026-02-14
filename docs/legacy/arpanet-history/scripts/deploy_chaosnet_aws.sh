#!/bin/bash
# Deploy Chaosnet shim to AWS and run connectivity test

set -e

AWS_HOST="ubuntu@34.227.223.186"
SSH_KEY="$HOME/.ssh/id_ed25519"
COMPOSE_FILE="docker-compose.arpanet.phase2.yml"

echo "========================================="
echo "Chaosnet Shim AWS Deployment"
echo "========================================="
echo ""

# Check SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    exit 1
fi

echo "📡 Connecting to AWS instance..."
ssh -i "$SSH_KEY" "$AWS_HOST" << 'EOF'
set -e

cd brfid.github.io

echo "📥 Pulling latest code..."
git pull origin main

echo "🏗️  Rebuilding containers..."
docker compose -f docker-compose.arpanet.phase2.yml down
docker compose -f docker-compose.arpanet.phase2.yml build chaosnet-shim

echo "🚀 Starting topology..."
docker compose -f docker-compose.arpanet.phase2.yml up -d

echo "⏳ Waiting for startup (30s)..."
sleep 30

echo "📊 Container status:"
docker compose -f docker-compose.arpanet.phase2.yml ps

echo ""
echo "✅ Deployment complete"
EOF

echo ""
echo "🧪 Running connectivity test..."
ssh -i "$SSH_KEY" "$AWS_HOST" << 'EOF'
cd brfid.github.io

# Use python3 (not venv on remote)
python3 arpanet/scripts/test_chaosnet_connectivity.py \
    --output build/arpanet/analysis/chaosnet-connectivity.json

# Show results
echo ""
echo "📄 Test results:"
cat build/arpanet/analysis/chaosnet-connectivity.json
EOF

echo ""
echo "========================================="
echo "✅ Deployment and test complete"
echo "========================================="
