#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Export Module

This module exports data from the SQLite database to JSON files
for consumption by the React dashboard. It creates both individual
model JSON files and an aggregated index file.

The exported JSON structure matches the format expected by the
frontend TypeScript interfaces.

Author: GPAI Documentation Pipeline
Date: November 2024
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

# Path configurations
DB = Path("data/model_docs.db")
OUT_DIR = Path("data/models")
SITE_AGG = Path("site/data/models.json")

# Ensure output directories exist
OUT_DIR.mkdir(parents=True, exist_ok=True)
SITE_AGG.parent.mkdir(parents=True, exist_ok=True)


def fetch_all() -> List[Dict[str, Any]]:
    """
    Fetch all model records from the database and format for export.
    
    Retrieves model data from SQLite and transforms it into the
    structure expected by the React frontend, including transparency
    scores and section completeness indicators.
    
    Returns:
        list: List of model dictionaries ready for JSON serialisation
    """
    # Connect to database and fetch all model records
    cx = sqlite3.connect(DB)
    cur = cx.cursor()
    
    # Select all relevant fields from the models table
    # Now includes section_data for full documentation text
    cur.execute(
        "SELECT name, provider, region, size, release_date, data, "
        "completeness_percent, bonus_stars, label_x, section_data, updated_at "
        "FROM models"
    )
    
    rows = cur.fetchall()
    cx.close()
    
    models = []
    # Process each database row into the frontend format
    for r in rows:
        name, provider, region, size, release, data, pct, stars, label, section_data, updated = r
        
        # Parse the JSON data field
        # Default to empty dict if NULL or invalid
        data = json.loads(data or "{}")
        
        # Parse the section_data field containing full documentation
        section_data = json.loads(section_data or "{}")
        
        # Build the model dictionary in the format expected by TypeScript
        model_dict = {
            "model_name": name,
            "provider": provider,
            "region": region,
            "size": size,
            "release_date": release,
            "transparency_score": {
                "overall": pct,
                # Convert _filled flags to numerical scores (0.0 or 1.0)
                # Only process dictionary entries (skip any scalar values)
                "sections": {
                    k: (1.0 if v.get("_filled") else 0.0) 
                    for k, v in data.items() 
                    if isinstance(v, dict)
                }
            },
            "stars": stars,
            "label_x": label,
            "last_updated": updated,
            # Include the full section documentation and sources
            "section_data": section_data
        }
        
        models.append(model_dict)
    
    return models

if __name__ == "__main__":
    # Check if database exists
    if not DB.exists():
        print(f"Error: Database not found at {DB}")
        print("Please run 'python scripts/db.py --init' first")
        exit(1)
    
    # Fetch all models from the database
    models = fetch_all()
    
    # Write the aggregated JSON file for the dashboard
    SITE_AGG.write_text(json.dumps(models, indent=2))
    print(f"Exported {len(models)} models to {SITE_AGG}")
    
    # Also write individual model files for detailed views
    # These can be used for deep-linking or API endpoints
    for model in models:
        filename = model["model_name"].lower().replace(" ", "-") + ".json"
        filepath = OUT_DIR / filename
        filepath.write_text(json.dumps(model, indent=2))
    
    print(f"Individual model files written to {OUT_DIR}")
    print("\nNext step: Run './scripts/sync_data.sh' to update the React app")