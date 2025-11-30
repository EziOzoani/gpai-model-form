#!/usr/bin/env python3
"""
Fix scoring consistency by synchronizing _filled flags with actual content.

This script addresses the issue where sections have content in section_data
but their _filled flags don't reflect this, causing incorrect scoring.
"""

import sqlite3
import json
from pathlib import Path

# Database path
DB = Path(__file__).parent.parent / "data" / "model_docs.db"

# Required sections for scoring
REQUIRED_SECTIONS = ["general", "properties", "distribution", "use", "data"]
BONUS_SECTIONS = ["training", "compute", "energy"]
ALL_SECTIONS = REQUIRED_SECTIONS + BONUS_SECTIONS


def has_real_content(section_content):
    """
    Check if a section has real content (not just empty or placeholder values).
    
    Returns True if the section has at least one non-empty field with meaningful content.
    """
    if not section_content or not isinstance(section_content, dict):
        return False
    
    # Check if any field has substantial content
    for field_name, field_value in section_content.items():
        if field_name.startswith('_'):
            continue
            
        if field_value:
            # Check if it's meaningful content (not just whitespace or placeholder)
            if isinstance(field_value, str):
                cleaned = field_value.strip()
                # Skip common placeholders
                if cleaned and cleaned.lower() not in ['n/a', 'na', 'none', 'null', '-', '']:
                    return True
            elif isinstance(field_value, (list, dict)) and field_value:
                return True
            elif field_value is not None:  # Numbers, booleans, etc.
                return True
    
    return False


def fix_scoring_consistency():
    """
    Main function to fix scoring consistency across all models.
    """
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    # Get all models
    cursor.execute("SELECT id, name, data, section_data FROM models")
    models = cursor.fetchall()
    
    fixed_count = 0
    issues_found = []
    
    for model_id, model_name, data_json, section_data_json in models:
        data = json.loads(data_json or '{}')
        section_data = json.loads(section_data_json or '{}')
        
        needs_update = False
        model_issues = []
        
        # Check each section
        for section in ALL_SECTIONS:
            # Get current _filled flag from data
            current_filled = data.get(section, {}).get('_filled', False)
            
            # Check if section_data has actual content
            has_content = has_real_content(section_data.get(section, {}))
            
            # If there's a mismatch, fix it
            if has_content != current_filled:
                if section not in data:
                    data[section] = {}
                
                data[section]['_filled'] = has_content
                needs_update = True
                
                issue = f"  {section}: _filled={current_filled} but has_content={has_content}"
                model_issues.append(issue)
        
        if needs_update:
            # Update the database
            cursor.execute(
                "UPDATE models SET data = ? WHERE id = ?",
                (json.dumps(data), model_id)
            )
            fixed_count += 1
            
            print(f"\nFixed {model_name}:")
            for issue in model_issues:
                print(issue)
            issues_found.extend(model_issues)
    
    conn.commit()
    
    # Now recalculate scores for all models
    print("\nRecalculating transparency scores...")
    cursor.execute("""
        UPDATE models
        SET completeness_percent = (
            SELECT CAST(COUNT(*) AS REAL) * 20
            FROM (
                SELECT json_extract(data, '$.general._filled') as filled
                WHERE filled = 1
                UNION ALL
                SELECT json_extract(data, '$.properties._filled') as filled  
                WHERE filled = 1
                UNION ALL
                SELECT json_extract(data, '$.distribution._filled') as filled
                WHERE filled = 1
                UNION ALL
                SELECT json_extract(data, '$.use._filled') as filled
                WHERE filled = 1
                UNION ALL
                SELECT json_extract(data, '$.data._filled') as filled
                WHERE filled = 1
            )
        ),
        bonus_stars = (
            SELECT COUNT(*)
            FROM (
                SELECT json_extract(data, '$.training._filled') as filled
                WHERE filled = 1
                UNION ALL
                SELECT json_extract(data, '$.compute._filled') as filled
                WHERE filled = 1
                UNION ALL
                SELECT json_extract(data, '$.energy._filled') as filled
                WHERE filled = 1
            )
        )
    """)
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Fixed {fixed_count} models")
    print(f"Total issues resolved: {len(issues_found)}")
    
    if fixed_count > 0:
        print("\n⚠️  IMPORTANT: Run the export script to update the site:")
        print("python scripts/db_export.py")
        print("./scripts/sync_data.sh")


if __name__ == "__main__":
    print("Fixing scoring consistency...")
    fix_scoring_consistency()