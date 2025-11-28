#!/usr/bin/env python3
"""
Create cleaned database with optimized storage using ID linking
"""

import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text_field(text):
    """Apply comprehensive text cleaning"""
    if not text:
        return ""
    
    # Remove HTML entities
    text = re.sub(r'&[a-z]+;', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove control characters
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    
    # Remove zero-width characters
    text = re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)
    
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    return text

def normalize_size(size):
    """Standardize model size formats"""
    if not size:
        return "Unknown"
    
    size = str(size).strip()
    
    # Convert common formats
    patterns = {
        r'(\d+)\s*billion': r'\1B',
        r'(\d+)\s*trillion': r'\1T',
        r'(\d+),(\d+)B': lambda m: f"{int(m.group(1))}.{m.group(2)}T",
        r'(\d+)b\b': r'\1B',
    }
    
    for pattern, replacement in patterns.items():
        if callable(replacement):
            size = re.sub(pattern, replacement, size, flags=re.IGNORECASE)
        else:
            size = re.sub(pattern, replacement, size, flags=re.IGNORECASE)
    
    return size

def extract_key_fields(data_json):
    """Extract and clean key fields from JSON data"""
    if not data_json:
        return {}
    
    try:
        data = json.loads(data_json) if isinstance(data_json, str) else data_json
    except:
        return {}
    
    cleaned = {}
    
    # Extract common fields
    field_mapping = {
        'description': ['description', 'summary', 'overview', 'about'],
        'architecture': ['architecture', 'model_architecture', 'type'],
        'parameters': ['parameters', 'model_size', 'params'],
        'license': ['license', 'license_type', 'licensing'],
        'use_cases': ['intended_use', 'use_cases', 'applications'],
        'limitations': ['limitations', 'restrictions', 'warnings']
    }
    
    for target_field, source_fields in field_mapping.items():
        for field in source_fields:
            if field in data and data[field]:
                cleaned[target_field] = clean_text_field(str(data[field]))
                break
    
    return cleaned

def create_cleaned_database():
    """Create optimized cleaned database with ID linking"""
    
    # Paths
    original_db = Path("data/model_docs.db")
    cleaned_db = Path("data/model_docs_cleaned.db")
    
    if not original_db.exists():
        logger.error(f"Original database not found: {original_db}")
        return
    
    # Create cleaned database
    cleaned_db.parent.mkdir(exist_ok=True)
    
    # Connect to databases
    conn_orig = sqlite3.connect(original_db)
    conn_clean = sqlite3.connect(cleaned_db)
    
    try:
        # Create optimized schema
        conn_clean.executescript("""
        -- Core model information
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            region TEXT,
            size TEXT,
            release_date TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, provider)
        );
        
        -- Cleaned text content (linked by model_id)
        CREATE TABLE IF NOT EXISTS model_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            description TEXT,
            architecture TEXT,
            parameters TEXT,
            license TEXT,
            use_cases TEXT,
            limitations TEXT,
            FOREIGN KEY (model_id) REFERENCES models (id)
        );
        
        -- Section data (normalized and linked)
        CREATE TABLE IF NOT EXISTS section_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            field_name TEXT NOT NULL,
            field_value TEXT,
            FOREIGN KEY (model_id) REFERENCES models (id)
        );
        
        -- Source tracking
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL,
            source_url TEXT NOT NULL,
            crawled_at TIMESTAMP,
            FOREIGN KEY (model_id) REFERENCES models (id)
        );
        
        -- Create indexes for performance
        CREATE INDEX idx_models_provider ON models(provider);
        CREATE INDEX idx_models_region ON models(region);
        CREATE INDEX idx_content_model ON model_content(model_id);
        CREATE INDEX idx_section_model ON section_content(model_id, section);
        CREATE INDEX idx_sources_model ON sources(model_id);
        """)
        
        # Process original data
        cursor_orig = conn_orig.cursor()
        cursor_clean = conn_clean.cursor()
        
        # Get all models
        cursor_orig.execute("SELECT * FROM models")
        models = cursor_orig.fetchall()
        
        logger.info(f"Processing {len(models)} models...")
        
        for model in models:
            # Extract fields (adjust based on actual schema)
            model_dict = {
                'name': clean_text_field(model[1]),
                'provider': clean_text_field(model[2]),
                'region': model[3],
                'size': normalize_size(model[4]),
                'release_date': model[5]
            }
            
            # Insert core model data
            cursor_clean.execute("""
                INSERT OR REPLACE INTO models (name, provider, region, size, release_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                model_dict['name'],
                model_dict['provider'],
                model_dict['region'],
                model_dict['size'],
                model_dict['release_date']
            ))
            
            model_id = cursor_clean.lastrowid
            
            # Process JSON data field
            if len(model) > 6 and model[6]:  # Assuming data is at index 6
                extracted = extract_key_fields(model[6])
                if extracted:
                    cursor_clean.execute("""
                        INSERT INTO model_content 
                        (model_id, description, architecture, parameters, license, use_cases, limitations)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        model_id,
                        extracted.get('description', ''),
                        extracted.get('architecture', ''),
                        extracted.get('parameters', ''),
                        extracted.get('license', ''),
                        extracted.get('use_cases', ''),
                        extracted.get('limitations', '')
                    ))
            
            # Process section data
            if len(model) > 7 and model[7]:  # Assuming section_data is at index 7
                try:
                    section_data = json.loads(model[7])
                    for section, fields in section_data.items():
                        if isinstance(fields, dict):
                            for field_name, field_value in fields.items():
                                if field_value:
                                    cleaned_value = clean_text_field(str(field_value))
                                    if cleaned_value:
                                        cursor_clean.execute("""
                                            INSERT INTO section_content 
                                            (model_id, section, field_name, field_value)
                                            VALUES (?, ?, ?, ?)
                                        """, (model_id, section, field_name, cleaned_value))
                except:
                    pass
        
        # Copy sources
        cursor_orig.execute("SELECT * FROM sources")
        sources = cursor_orig.fetchall()
        
        for source in sources:
            # Map original model name to new model_id
            cursor_clean.execute("""
                SELECT id FROM models WHERE name = ? AND provider = ?
            """, (source[1], source[2]))  # Adjust indices based on schema
            
            result = cursor_clean.fetchone()
            if result:
                new_model_id = result[0]
                cursor_clean.execute("""
                    INSERT INTO sources (model_id, source_url, crawled_at)
                    VALUES (?, ?, ?)
                """, (new_model_id, source[3], source[4]))  # Adjust indices
        
        conn_clean.commit()
        logger.info("Cleaned database created successfully")
        
        # Report statistics
        cursor_clean.execute("SELECT COUNT(*) FROM models")
        model_count = cursor_clean.fetchone()[0]
        
        cursor_clean.execute("SELECT COUNT(*) FROM model_content WHERE description != ''")
        content_count = cursor_clean.fetchone()[0]
        
        logger.info(f"Statistics:")
        logger.info(f"- Total models: {model_count}")
        logger.info(f"- Models with descriptions: {content_count}")
        logger.info(f"- Database size: {cleaned_db.stat().st_size / 1024 / 1024:.2f} MB")
        
    finally:
        conn_orig.close()
        conn_clean.close()

if __name__ == "__main__":
    create_cleaned_database()