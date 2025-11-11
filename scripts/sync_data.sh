#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Data Synchronisation Script
#
# This script copies the generated models.json file from the data pipeline
# to the React app's public directory. This ensures the frontend always
# has access to the latest model documentation data.
#
# Run this after executing db_export.py to update the UI data.
#
# Author: GPAI Documentation Pipeline
# Date: November 2024

set -euo pipefail

# Navigate to the script directory's parent (project root)
cd "$(dirname "$0")/.."

# Check if the source file exists
if [ ! -f "site/data/models.json" ]; then
    echo "Warning: site/data/models.json not found."
    echo "Please run 'python scripts/db_export.py' first to generate the data."
    exit 1
fi

# Copy the aggregated model data to the React app's public directory
echo "Synchronising model data to React app..."
cp site/data/models.json site/public/data/models.json

# Also copy individual model files if they exist
if [ -d "data/models" ] && [ "$(ls -A data/models/*.json 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "Copying individual model files..."
    mkdir -p site/public/data/models
    cp data/models/*.json site/public/data/models/ 2>/dev/null || true
fi

echo "Data synchronisation complete."