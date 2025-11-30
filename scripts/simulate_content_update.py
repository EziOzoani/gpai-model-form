#!/usr/bin/env python3
"""
Simulate content updates to test the enhanced pipeline
"""

import sqlite3
import json
from datetime import datetime

def add_content_to_model(model_name="Google Gemini 2.5 Pro"):
    """Add some content to an existing model to simulate updates"""
    
    conn = sqlite3.connect("data/model_docs.db")
    
    # Get current section_data
    cursor = conn.execute(
        "SELECT section_data FROM models WHERE name = ?", 
        (model_name,)
    )
    row = cursor.fetchone()
    
    if row and row[0]:
        section_data = json.loads(row[0])
    else:
        section_data = {}
    
    # Add new content to simulate scraper updates
    if 'training' not in section_data:
        section_data['training'] = {}
    
    section_data['training']['methodology'] = """
    The model was trained using advanced transformer architecture with 
    reinforcement learning from human feedback (RLHF). Training involved 
    multiple stages including pretraining on diverse internet text, 
    supervised fine-tuning, and iterative refinement based on human preferences.
    """
    
    section_data['training']['hardware'] = "TPU v4 pods with 4096 chips"
    section_data['training']['duration'] = "6 months of continuous training"
    
    # Add energy information
    if 'energy' not in section_data:
        section_data['energy'] = {}
    
    section_data['energy']['consumption'] = "Estimated 500 MWh total"
    section_data['energy']['methodology'] = "Measured using datacenter PUE metrics"
    
    # Update the database
    conn.execute("""
        UPDATE models 
        SET section_data = ?, 
            updated_at = ?
        WHERE name = ?
    """, (json.dumps(section_data), datetime.now().isoformat(), model_name))
    
    conn.commit()
    conn.close()
    
    print(f"Added training and energy content to {model_name}")

if __name__ == "__main__":
    # Add content to trigger update
    add_content_to_model("Google Gemini 2.5 Pro")
    add_content_to_model("Mistral Mistral 7B")
    print("\nContent updates simulated. Run status check to see changes.")