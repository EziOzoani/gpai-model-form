#!/usr/bin/env python3
"""Debug scoring issues for models like Google Nano Banana"""

import sqlite3
import json
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "model_docs.db"

def debug_model(model_name):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT data, section_data, completeness_percent FROM models WHERE name = ?",
        (model_name,)
    )
    
    result = cursor.fetchone()
    if result:
        data, section_data, score = result
        data_dict = json.loads(data or '{}')
        section_data_dict = json.loads(section_data or '{}')
        
        print(f"\n=== Debugging {model_name} ===")
        print(f"Current score: {score}%")
        
        print("\n--- DATA field (used for _filled flags) ---")
        print(json.dumps(data_dict, indent=2))
        
        print("\n--- SECTION_DATA field (actual content) ---")
        print(json.dumps(section_data_dict, indent=2))
        
        print("\n--- Analysis ---")
        for section in ['general', 'properties', 'distribution', 'use', 'data', 'training', 'compute', 'energy']:
            filled_flag = data_dict.get(section, {}).get('_filled', False)
            has_content = bool(section_data_dict.get(section))
            print(f"{section}: _filled={filled_flag}, has_content={has_content}")
    
    conn.close()

if __name__ == "__main__":
    debug_model("Google Nano Banana 🍌")