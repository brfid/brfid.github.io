#!/bin/bash
# Quick publish script - Mode 3 (local/fast)
# Creates a dated tag and pushes for fast publish

set -e

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M)
TAG_NAME="publish-fast-${TIMESTAMP}"

echo "========================================="
echo "Fast Publish (Mode 3)"
echo "========================================="
echo ""
echo "Tag: ${TAG_NAME}"
echo "Mode: Local (host compiler, fast)"
echo "Expected time: 3-5 minutes"
echo ""

# Confirm
read -p "Create tag and push? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Create and push tag
echo "Creating tag..."
git tag "${TAG_NAME}"

echo "Pushing tag..."
git push origin "${TAG_NAME}"

echo ""
echo "✅ Tag pushed successfully!"
echo ""
echo "View progress:"
echo "  https://github.com/brfid/brfid.github.io/actions"
echo ""
echo "Site will be available at:"
echo "  https://brfid.github.io/"
echo ""
