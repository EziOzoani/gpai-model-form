#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Test Script for GPAI Documentation Scrapers
#
# This script runs a complete test of the scraping pipeline:
# 1. Initialises the database
# 2. Runs official source scrapers
# 3. Evaluates initial completeness
# 4. Runs gap-filling scraper
# 5. Evaluates final completeness
# 6. Exports data for the UI
#
# Author: GPAI Documentation Pipeline
# Date: November 2024

set -euo pipefail

echo "=========================================="
echo "GPAI Documentation Scraper Test"
echo "=========================================="
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Clean up old test data
echo "Cleaning up old test data..."
rm -f data/model_docs.db
rm -f data/models/*.json
rm -rf logs/
mkdir -p logs data/models

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Initialise database
echo -e "\n1. Initialising database..."
python scripts/db.py --init

# Run official scrapers (limited for testing)
echo -e "\n2. Running official source scrapers..."
echo "   Note: This will make real HTTP requests to official sites"
python scripts/crawl.py || echo "Some scrapers failed (this is normal for testing)"

# First evaluation
echo -e "\n3. Initial data quality evaluation..."
python scripts/evaluate.py

# Run gap-filling scraper on a few models
echo -e "\n4. Running gap-filling scraper (test mode)..."
python scripts/crawl_general.py --test

# Final evaluation
echo -e "\n5. Final data quality evaluation..."
python scripts/evaluate.py --export data/quality_report.json

# Export data for UI
echo -e "\n6. Exporting data for UI..."
python scripts/db_export.py

# Sync to React app
if [ -f "scripts/sync_data.sh" ]; then
    echo -e "\n7. Syncing data to React app..."
    ./scripts/sync_data.sh
fi

echo -e "\n=========================================="
echo "Test complete!"
echo "=========================================="
echo ""
echo "Results:"
echo "- Database: data/model_docs.db"
echo "- Model JSONs: data/models/"
echo "- Quality report: data/quality_report.json"
echo "- Logs: logs/"
echo ""
echo "To view in the UI:"
echo "1. cd site"
echo "2. npm run dev"
echo "3. Open http://localhost:5173"