#!/bin/bash
# Distributed vintage publish helper
# Creates a dated publish tag and pushes for full edcloud-backed pipeline

set -e

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M)
TAG_NAME="publish-vintage-${TIMESTAMP}"

echo "========================================="
echo "Distributed Vintage Publish"
echo "========================================="
echo ""
echo "Tag: ${TAG_NAME}"
echo "Mode: Distributed vintage (authentic BSD pipeline)"
echo "Expected time: 10-12 minutes"
echo ""
echo "This will:"
echo "  - Start edcloud host for distributed vintage build"
echo "  - Run authentic 4.3BSD + 2.11BSD stages"
echo "  - Generate site with merged build logs"
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
echo "Build logs viewer will be at:"
echo "  https://brfid.github.io/logs/"
echo ""
