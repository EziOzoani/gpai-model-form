#!/usr/bin/env python3
"""
Generate JSON data for the visual dashboard from the cleaned database.
This bridges the gap between the scraped data and the React dashboard.
"""
import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

def calculate_section_score(section_data):
    """Calculate score for a section based on filled fields."""
    if not section_data or not isinstance(section_data, dict):
        return 0.0
    
    # If the section has _filled flag, use it
    if section_data.get('_filled'):
        # Count how many actual fields (excluding _filled) have values
        fields_with_values = sum(1 for k, v in section_data.items() 
                                if k != '_filled' and v and v != '')
        total_fields = len([k for k in section_data.keys() if k != '_filled'])
        
        if total_fields > 0:
            return min(1.0, fields_with_values / max(1, total_fields * 0.5))  # Need at least 50% fields
        return 1.0 if fields_with_values > 0 else 0.0
    
    return 0.0

def calculate_transparency_score(data):
    """Calculate overall transparency score using the same logic as the UI."""
    sections = {
        'general': data.get('general', {}),
        'properties': data.get('properties', {}),
        'distribution': data.get('distribution', {}),
        'use': data.get('use', {}),
        'data': data.get('data', {}),
        'training': data.get('training', {}),
        'compute': data.get('compute', {}),
        'energy': data.get('energy', {})
    }
    
    # Calculate individual section scores
    section_scores = {}
    for section_name, section_data in sections.items():
        section_scores[section_name] = calculate_section_score(section_data)
    
    # Weight sections (matching UI logic)
    weights = {
        'general': 1.0,
        'properties': 1.0,
        'distribution': 1.0,
        'use': 1.5,  # Higher weight for use cases
        'data': 1.5,  # Higher weight for data transparency
        'training': 1.0,
        'compute': 1.0,
        'energy': 1.0
    }
    
    total_weight = sum(weights.values())
    weighted_sum = sum(section_scores[s] * weights[s] for s in sections)
    
    overall_score = (weighted_sum / total_weight) * 100
    
    return {
        'overall': round(overall_score),
        'sections': section_scores
    }

def generate_dashboard_data():
    """Generate JSON data for the dashboard."""
    # Connect to the cleaned database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'scraped_not_cleaned_final.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all models
    cursor.execute("""
        SELECT name, provider, region, size, release_date, data, completeness_percent
        FROM models
        ORDER BY provider, name
    """)
    
    models = []
    
    for row in cursor.fetchall():
        name, provider, region, size, release_date, data_json, db_completeness = row
        
        try:
            data = json.loads(data_json) if data_json else {}
        except:
            data = {}
        
        # Recalculate transparency score using UI logic
        transparency = calculate_transparency_score(data)
        
        # Create model entry for dashboard
        model_entry = {
            'id': f"{provider.lower().replace(' ', '-')}-{name.lower().replace(' ', '-')}",
            'name': name,
            'provider': provider,
            'region': region or 'Unknown',
            'size': size or 'Unknown',
            'releaseDate': release_date or '2024-01-01',
            'transparencyScore': transparency['overall'],
            'sections': {
                'general': transparency['sections']['general'],
                'properties': transparency['sections']['properties'],
                'distribution': transparency['sections']['distribution'],
                'use': transparency['sections']['use'],
                'data': transparency['sections']['data'],
                'training': transparency['sections']['training'],
                'compute': transparency['sections']['compute'],
                'energy': transparency['sections']['energy']
            },
            'rawData': data  # Include raw data for detail view
        }
        
        models.append(model_entry)
    
    conn.close()
    
    # Write to dashboard data file
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'docu-bloom-grid-main',
        'src',
        'data',
        'models.json'
    )
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'models': models,
            'lastUpdated': datetime.now().isoformat(),
            'totalModels': len(models)
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Generated dashboard data for {len(models)} models")
    print(f"Output: {output_path}")
    
    # Print summary
    avg_score = sum(m['transparencyScore'] for m in models) / len(models) if models else 0
    print(f"\nSummary:")
    print(f"- Average transparency score: {avg_score:.1f}%")
    print(f"- Models by region: {dict((r, sum(1 for m in models if m['region'] == r)) for r in set(m['region'] for m in models))}")
    print(f"- Models by provider: {dict((p, sum(1 for m in models if m['provider'] == p)) for p in set(m['provider'] for m in models))}")

if __name__ == "__main__":
    generate_dashboard_data()