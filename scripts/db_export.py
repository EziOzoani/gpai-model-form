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
import sys
sys.path.insert(0, str(Path(__file__).parent))
from ranking_calculator import RankingCalculator, BONUS_SECTIONS

# Path configurations
DB = Path("data/model_docs.db")
OUT_DIR = Path("data/models")
SITE_AGG = Path("site/data/models.json")

# Ensure output directories exist
OUT_DIR.mkdir(parents=True, exist_ok=True)
SITE_AGG.parent.mkdir(parents=True, exist_ok=True)


def calculate_content_score(value: Any) -> float:
    """Calculate completeness score based on word count."""
    if not value:
        return 0.0
    
    # Handle lists (e.g., modalities, channels)
    if isinstance(value, list):
        if not value:
            return 0.0
        text = ' '.join(str(item) for item in value)
    # Handle dictionaries with text/source structure
    elif isinstance(value, dict):
        if 'text' in value:
            text = str(value['text'])
        else:
            return 0.0
    else:
        text = str(value)
    
    # Count words
    words = text.strip().split()
    word_count = len(words)
    
    # Weighted scoring based on word count
    if word_count == 0:
        return 0.0
    elif word_count == 1:
        return 0.2  # 20% for single words (model IDs, etc.)
    elif word_count <= 3:
        return 0.4  # 40% for short names/terms
    elif word_count <= 5:
        return 0.6  # 60% for brief descriptions
    elif word_count <= 10:
        return 0.8  # 80% for moderate descriptions
    else:
        return 1.0  # 100% for detailed descriptions

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
        
        # Use the completeness_percent from database instead of recalculating
        overall_percentage = pct if pct is not None else 0
        
        # Calculate section scores and get section info for star indicators
        section_scores = {}
        section_info = RankingCalculator.get_all_sections_info()
        
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                # Check if section has _filled flag
                if section_content.get('_filled'):
                    section_scores[section_name] = 1.0
                else:
                    section_scores[section_name] = 0.0
        
        # Merge content from data field into section_data
        # This ensures we capture content stored in either location
        for section_name, section_content in data.items():
            if isinstance(section_content, dict):
                # Initialize section if it doesn't exist
                if section_name not in section_data:
                    section_data[section_name] = {}
                
                # Merge fields from data into section_data
                for field_name, field_value in section_content.items():
                    if field_name.startswith('_'):
                        continue
                    # Include all non-empty fields
                    if field_value and field_name not in section_data[section_name]:
                        section_data[section_name][field_name] = field_value
        
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
            "star_sections": BONUS_SECTIONS,
            "section_info": section_info,
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