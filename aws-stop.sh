#!/bin/bash
# Stop edcloud build host
# Note: This script is for local convenience. GitHub Actions uses 'edcloud down' directly.

set -e

cd "$(dirname "$0")/../edcloud" 2>/dev/null || {
  echo "Error: edcloud not found. Expected at ../edcloud/"
  echo "This project now uses edcloud for distributed vintage builds."
  exit 1
}

source .venv/bin/activate
exec edcloud down
