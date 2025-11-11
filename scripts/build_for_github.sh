#!/usr/bin/env bash
# Build script for GitHub Pages deployment
# 
# This script builds the React app and prepares it for deployment.
# Run this before committing and pushing to GitHub.
#
# Author: GPAI Documentation Pipeline
# Date: November 2024

set -euo pipefail

echo "==========================================="
echo "Building GPAI Dashboard for GitHub Pages"
echo "==========================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Ensure we have latest data
if [ ! -f "site/data/models.json" ]; then
    echo "Warning: No model data found. Running export..."
    python scripts/db_export.py
    ./scripts/sync_data.sh
fi

# Navigate to React app
cd site

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf dist

# Build for production
echo "Building React app..."
npm run build

# Create .nojekyll file in dist to bypass Jekyll processing
touch dist/.nojekyll

# Success message
echo ""
echo "==========================================="
echo "Build complete!"
echo "==========================================="
echo ""
echo "Next steps:"
echo "1. cd .."
echo "2. git add -A"
echo "3. git commit -m 'Update dashboard and data'"
echo "4. git push origin main"
echo ""
echo "GitHub Pages will automatically deploy from the workflow."
echo "Check deployment at: https://eziozoani.github.io/gpai-model-form/"