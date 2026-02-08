#!/bin/bash
# ARPANET publish script - Mode 4 (full stack)
# Creates a dated tag and pushes for full ARPANET build

set -e

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M)
TAG_NAME="publish-arpanet-${TIMESTAMP}"

echo "========================================="
echo "ARPANET Publish (Mode 4)"
echo "========================================="
echo ""
echo "Tag: ${TAG_NAME}"
echo "Mode: ARPANET (full network stack)"
echo "Expected time: 10-12 minutes"
echo ""
echo "This will:"
echo "  - Start Phase 2 ARPANET containers (VAX + IMP1 + IMP2 + PDP10)"
echo "  - Compile on authentic 4.3BSD"
echo "  - Generate site with ARPANET logs"
echo "  - Deploy to GitHub Pages"
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
echo "ARPANET logs will be at:"
echo "  https://brfid.github.io/arpanet-logs/"
echo ""
