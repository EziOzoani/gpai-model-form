#!/usr/bin/env python3
"""
Properly fix scoring by checking both data and section_data fields.

This addresses the issue where some models store content in 'data' field
while others use 'section_data' field.
"""

import sqlite3
import json
from pathlib import Path

DB = Path(__file__).parent.parent / "data" / "model_docs.db"

REQUIRED_SECTIONS = ["general", "properties", "distribution", "use", "data"]
BONUS_SECTIONS = ["training", "compute", "energy"]
ALL_SECTIONS = REQUIRED_SECTIONS + BONUS_SECTIONS


def has_real_content_in_section(section_content):
    """Check if a section has real content (not just _filled flag)"""
    if not section_content or not isinstance(section_content, dict):
        return False
    
    # Check each field in the section
    for field_name, field_value in section_content.items():
        # Skip metadata fields
        if field_name.startswith('_'):
            continue
        
        # Check if field has meaningful content
        if field_value:
            if isinstance(field_value, str):
                cleaned = field_value.strip()
                # Skip empty or placeholder values
                if cleaned and cleaned.lower() not in ['n/a', 'na', 'none', 'null', '-', '', 'tbd']:
                    return True
            elif isinstance(field_value, list) and field_value:
                # Non-empty list
                return True
            elif isinstance(field_value, dict) and field_value:
                # Non-empty dict (but check if it's not just nested metadata)
                if any(not k.startswith('_') for k in field_value.keys()):
                    return True
            elif isinstance(field_value, (int, float, bool)):
                # Numbers and booleans are valid content
                return True
    
    return False


def fix_all_models():
    """Fix scoring for all models in the database"""
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, data, section_data FROM models")
    models = cursor.fetchall()
    
    fixed_count = 0
    detailed_log = []
    
    for model_id, model_name, data_json, section_data_json in models:
        data = json.loads(data_json or '{}')
        section_data = json.loads(section_data_json or '{}')
        
        needs_update = False
        model_changes = []
        
        for section in ALL_SECTIONS:
            # Get current _filled flag
            current_filled = data.get(section, {}).get('_filled', False)
            
            # Check for content in BOTH places:
            # 1. In the data field itself (excluding _filled)
            data_section = data.get(section, {})
            has_content_in_data = has_real_content_in_section(data_section)
            
            # 2. In the section_data field
            section_data_section = section_data.get(section, {})
            has_content_in_section_data = has_real_content_in_section(section_data_section)
            
            # Section has content if it's in either place
            has_content = has_content_in_data or has_content_in_section_data
            
            # Update _filled flag if needed
            if has_content != current_filled:
                if section not in data:
                    data[section] = {}
                    
                data[section]['_filled'] = has_content
                needs_update = True
                
                change = f"  {section}: _filled {current_filled} → {has_content}"
                if has_content_in_data and has_content_in_section_data:
                    change += " (content in both data and section_data)"
                elif has_content_in_data:
                    change += " (content in data field)"
                elif has_content_in_section_data:
                    change += " (content in section_data field)"
                    
                model_changes.append(change)
        
        if needs_update:
            # Update the database
            cursor.execute(
                "UPDATE models SET data = ? WHERE id = ?",
                (json.dumps(data), model_id)
            )
            fixed_count += 1
            
            log_entry = f"\n{model_name}:"
            for change in model_changes:
                log_entry += f"\n{change}"
            detailed_log.append(log_entry)
            print(log_entry)
    
    conn.commit()
    
    # Recalculate completeness scores
    print("\n\nRecalculating transparency scores...")
    
    # For each model, calculate score based on _filled flags
    cursor.execute("SELECT id, data FROM models")
    for model_id, data_json in cursor.fetchall():
        data = json.loads(data_json or '{}')
        
        # Count filled required sections
        filled_required = sum(1 for s in REQUIRED_SECTIONS 
                            if data.get(s, {}).get('_filled', False))
        completeness = int((filled_required / len(REQUIRED_SECTIONS)) * 100)
        
        # Count bonus sections
        bonus = sum(1 for s in BONUS_SECTIONS 
                   if data.get(s, {}).get('_filled', False))
        
        cursor.execute(
            "UPDATE models SET completeness_percent = ?, bonus_stars = ? WHERE id = ?",
            (completeness, bonus, model_id)
        )
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Fixed {fixed_count} models")
    print(f"\n📋 Summary of changes:{len(detailed_log)} models updated")
    
    if fixed_count > 0:
        print("\n⚠️  Run these commands to update the site:")
        print("python scripts/db_export.py")
        print("./scripts/sync_data.sh")


if __name__ == "__main__":
    print("Fixing scoring properly (checking both data and section_data fields)...\n")
    fix_all_models()