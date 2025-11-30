#!/usr/bin/env python3
"""Check what data Mistral 7B actually has in the database"""

import sqlite3
import json
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "model_docs.db"

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute(
    "SELECT data, section_data FROM models WHERE name = 'Mistral Mistral 7B'"
)

result = cursor.fetchone()
if result:
    data, section_data = result
    data_dict = json.loads(data or '{}')
    section_data_dict = json.loads(section_data or '{}')
    
    print("=== DATA field ===")
    print(json.dumps(data_dict, indent=2))
    
    print("\n=== SECTION_DATA field ===")
    print(json.dumps(section_data_dict, indent=2))

conn.close()