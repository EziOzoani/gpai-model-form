#!/usr/bin/env python3
"""
Recalculate all model percentages using the new ranking calculator.

This script updates the database with correct percentages based on
the new calculation method (all 8 sections instead of just 5).

Author: GPAI Documentation Pipeline
Date: December 2024
"""

import sqlite3
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ranking_calculator import RankingCalculator

def recalculate_all_percentages():
    """Recalculate percentages for all models in the database."""
    
    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "model_docs.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Get all models with their data
    cursor = conn.execute("""
        SELECT id, name, data 
        FROM models
        WHERE data IS NOT NULL
    """)
    
    models = cursor.fetchall()
    print(f"Found {len(models)} models to update")
    
    updated_count = 0
    
    for model in models:
        try:
            # Parse the JSON data
            data = json.loads(model['data']) if model['data'] else {}
            
            if not data:
                continue
                
            # Calculate using the new method
            result = RankingCalculator.calculate_from_section_map(data)
            new_percentage = result['completeness_percent']
            new_stars = result['bonus_stars']
            
            # Update the database
            conn.execute("""
                UPDATE models 
                SET completeness_percent = ?, bonus_stars = ?
                WHERE id = ?
            """, (new_percentage, new_stars, model['id']))
            
            updated_count += 1
            print(f"Updated {model['name']}: {new_percentage}% ({new_stars} stars)")
            
        except Exception as e:
            print(f"Error updating {model['name']}: {e}")
            continue
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\nSuccessfully updated {updated_count} models")
    print("Run 'python scripts/db_export.py' to regenerate the UI data")


if __name__ == "__main__":
    recalculate_all_percentages()