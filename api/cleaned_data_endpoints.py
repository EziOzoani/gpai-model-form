#!/usr/bin/env python3
"""
API endpoints for serving cleaned model data with Code of Practice filtering
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent / 'scripts'))
from ranking_calculator import RankingCalculator
import json

app = Flask(__name__)
CORS(app)

CLEANED_DB_PATH = Path("data/model_docs_cleaned.db")
ORIGINAL_DB_PATH = Path("data/model_docs.db")

# Code of Practice signatories and their signing dates
CODE_OF_PRACTICE_SIGNATORIES = {
    "OpenAI": "2024-05-16",
    "Google": "2024-05-16", 
    "Microsoft": "2024-05-16",
    "Meta": "2024-05-16",
    "Anthropic": "2024-05-16",
    "Mistral AI": "2024-05-16",
    "Cohere": "2024-09-20",  # September signatory
    "Aleph Alpha": "2024-09-20",
    "IBM": "2024-09-20"
}

def get_transparency_score(model_id, conn):
    """Calculate transparency score for a model"""
    cursor = conn.execute("""
        SELECT COUNT(DISTINCT section) as sections,
               COUNT(*) as total_fields
        FROM section_content 
        WHERE model_id = ?
    """, (model_id,))
    
    row = cursor.fetchone()
    if row:
        sections = row[0]
        fields = row[1]
        # Use centralized calculation
        return RankingCalculator.calculate_transparency_score(sections, fields)
    return 0

def is_code_of_practice_signatory(provider, cutoff_date):
    """Check if provider is a Code of Practice signatory by cutoff date"""
    if provider not in CODE_OF_PRACTICE_SIGNATORIES:
        return False
    
    signing_date = CODE_OF_PRACTICE_SIGNATORIES[provider]
    return signing_date <= cutoff_date

@app.route('/api/models/cleaned', methods=['GET'])
def get_cleaned_models():
    """Get all models from cleaned database with filters"""
    try:
        # Get filter parameters
        region_filter = request.args.get('region', 'all')
        size_filter = request.args.get('size', 'all')
        cop_filter = request.args.get('code_of_practice', 'all')
        cutoff_date = request.args.get('cutoff', '2024-09-30')  # Default September
        
        conn = sqlite3.connect(CLEANED_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Build query with filters
        query = """
            SELECT m.*, 
                   COUNT(DISTINCT sc.section) as sections_documented,
                   GROUP_CONCAT(DISTINCT sc.section) as sections_list
            FROM models m
            LEFT JOIN section_content sc ON m.id = sc.model_id
            WHERE 1=1
        """
        params = []
        
        # Region filter
        if region_filter != 'all':
            query += " AND m.region = ?"
            params.append(region_filter)
        
        # Size filter
        if size_filter != 'all':
            if size_filter == 'big':
                query += " AND (m.size LIKE '%Big%' OR m.size LIKE '%Large%' OR m.size LIKE '%T%')"
            else:
                query += " AND (m.size LIKE '%Small%' OR m.size LIKE '%Medium%' OR m.size LIKE '%B%')"
        
        query += " GROUP BY m.id"
        
        cursor = conn.execute(query, params)
        models = []
        
        for row in cursor:
            model_dict = dict(row)
            
            # Calculate transparency score
            model_dict['transparency_score'] = get_transparency_score(row['id'], conn)
            
            # Check Code of Practice status
            is_signatory = is_code_of_practice_signatory(row['provider'], cutoff_date)
            model_dict['code_of_practice_signatory'] = is_signatory
            
            # Apply Code of Practice filter
            if cop_filter == 'signatories' and not is_signatory:
                continue
            elif cop_filter == 'non_signatories' and is_signatory:
                continue
            
            # Get section data for UI
            section_cursor = conn.execute("""
                SELECT section, field_name, field_value
                FROM section_content
                WHERE model_id = ?
            """, (row['id'],))
            
            section_data = {}
            for section_row in section_cursor:
                section = section_row[0]
                if section not in section_data:
                    section_data[section] = {}
                section_data[section][section_row[1]] = section_row[2]
            
            model_dict['section_data'] = section_data
            
            # Get content data
            content_cursor = conn.execute("""
                SELECT description, architecture, parameters, license, use_cases, limitations
                FROM model_content
                WHERE model_id = ?
            """, (row['id'],))
            
            content_row = content_cursor.fetchone()
            if content_row:
                model_dict['content'] = dict(content_row)
            
            models.append(model_dict)
        
        conn.close()
        
        # Calculate cutoff statistics
        total_signatories = sum(1 for m in models if m['code_of_practice_signatory'])
        
        return jsonify({
            "models": models,
            "total": len(models),
            "signatories_count": total_signatories,
            "cutoff_date": cutoff_date,
            "last_updated": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/models/export/cleaned', methods=['GET'])
def export_cleaned_data():
    """Export cleaned data in format compatible with existing UI"""
    try:
        conn = sqlite3.connect(CLEANED_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get all models with their data
        cursor = conn.execute("""
            SELECT m.*, 
                   COUNT(DISTINCT sc.section) as sections_documented
            FROM models m
            LEFT JOIN section_content sc ON m.id = sc.model_id
            GROUP BY m.id
        """)
        
        export_data = []
        
        for row in cursor:
            # Get section data
            section_cursor = conn.execute("""
                SELECT section, field_name, field_value
                FROM section_content
                WHERE model_id = ?
            """, (row['id'],))
            
            section_data = {}
            for section_row in section_cursor:
                section = section_row[0]
                if section not in section_data:
                    section_data[section] = {}
                section_data[section][section_row[1]] = section_row[2]
            
            # Format for UI compatibility
            model_data = {
                "name": row['name'],
                "provider": row['provider'],
                "region": row['region'],
                "size": row['size'],
                "release_date": row['release_date'],
                "data": {},  # Legacy field
                "section_data": json.dumps(section_data),
                "completeness_percent": get_transparency_score(row['id'], conn),
                "bonus_stars": 0,
                "label_x": None,
                "code_of_practice_signatory": is_code_of_practice_signatory(
                    row['provider'], 
                    request.args.get('cutoff', '2024-09-30')
                ),
                "provenance_url": None,
                "updated_at": datetime.now().isoformat()
            }
            
            export_data.append(model_data)
        
        conn.close()
        
        # Write to JSON file for UI consumption
        output_path = Path("site/public/data/models_cleaned.json")
        output_path.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_path, 'w') as f:
            json.dump({
                "models": export_data,
                "last_updated": datetime.now().isoformat(),
                "total_count": len(export_data),
                "source": "cleaned_database"
            }, f, indent=2)
        
        return jsonify({
            "status": "success",
            "exported": len(export_data),
            "path": str(output_path)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/signatories', methods=['GET'])
def get_signatories():
    """Get list of Code of Practice signatories with dates"""
    cutoff = request.args.get('cutoff', '2024-09-30')
    
    signatories = []
    for provider, date in CODE_OF_PRACTICE_SIGNATORIES.items():
        if date <= cutoff:
            signatories.append({
                "provider": provider,
                "signing_date": date,
                "batch": "January" if date <= "2024-05-31" else "September"
            })
    
    return jsonify({
        "signatories": signatories,
        "cutoff_date": cutoff,
        "total": len(signatories)
    })

if __name__ == '__main__':
    print("Starting Cleaned Data API on http://localhost:5002")
    app.run(debug=True, port=5002)