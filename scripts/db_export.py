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


def has_meaningful_content(value: Any) -> bool:
    """Check if content has at least 5 words."""
    if not value:
        return False
    
    # Handle lists (e.g., modalities, channels)
    if isinstance(value, list):
        # Join list items and count words
        text = ' '.join(str(item) for item in value)
    # Handle dictionaries with text/source structure
    elif isinstance(value, dict):
        if 'text' in value:
            text = str(value['text'])
        else:
            return False
    else:
        text = str(value)
    
    words = text.strip().split()
    return len(words) >= 5

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
        data = json.loads(data or "{}")
        section_data = json.loads(section_data or "{}")
        
        # Calculate section scores based on actual content
        section_scores = {}
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                # Count fields with meaningful content (5+ words)
                filled_fields = 0
                total_fields = 0
                for field_name, field_value in section_content.items():
                    if field_name.startswith('_'):
                        continue
                    total_fields += 1
                    if has_meaningful_content(field_value):
                        filled_fields += 1
                
                # Score is percentage of fields with content
                if total_fields > 0:
                    section_scores[section_name] = filled_fields / total_fields
                else:
                    section_scores[section_name] = 0.0
        
        # Build section_data from actual data if empty
        if not section_data:
            for section_name, section_content in data.items():
                if isinstance(section_content, dict):
                    section_data[section_name] = {}
                    for field_name, field_value in section_content.items():
                        if field_name.startswith('_'):
                            continue
                        if has_meaningful_content(field_value):
                            section_data[section_name][field_name] = field_value
        
        # Calculate overall score
        total_score = sum(section_scores.values())
        num_sections = len(section_scores) if section_scores else 1
        overall_percentage = int((total_score / num_sections) * 100) if num_sections > 0 else 0
        
        model_dict = {
            "model_name": name,
            "provider": provider,
            "region": region,
            "size": size,
            "release_date": release,
            "transparency_score": {
                "overall": overall_percentage,
                "sections": section_scores
            },
            "stars": stars,
            "label_x": label,
            "last_updated": updated,
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