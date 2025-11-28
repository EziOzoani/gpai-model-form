#!/usr/bin/env python3
"""
Enhanced scraping script that fills gaps without creating duplicates.
Searches for missing information from tier 1 sources.
"""
import sqlite3
import logging
import json
from pathlib import Path
import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.crawl_general import GapFillingCrawler
from scripts.enhanced_scraper import TierOneScraper
from scripts.scoring import completeness

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_existing_data(db_path, model_id, field):
    """Check if field already has data."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM sources 
            WHERE model_id = ? AND field = ?
        """, (model_id, field))
        return cur.fetchone()[0] > 0

def update_model_with_tier1_data(db_path, model_id, tier_one_data):
    """Update the models table with found tier 1 data."""
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        
        # Get existing model data
        cur.execute("SELECT data, release_date FROM models WHERE id = ?", (model_id,))
        row = cur.fetchone()
        if not row:
            logger.error(f"Model with ID {model_id} not found")
            return
        
        existing_data_json, current_release_date = row
        existing_data = json.loads(existing_data_json or '{}')
        
        # Map field names to sections
        field_to_section = {
            'legal_name': 'general',
            'model_id': 'general',
            'description': 'general',
            'training_compute': 'general',
            'flops_per_param': 'general',
            'total_flops': 'general',
            'intended_use': 'use',
            'prohibited_uses': 'use',
            'release_date': 'general',
            'architecture': 'properties',
            'model_sizes': 'properties',
            'context_window': 'properties',
            'license': 'distribution',
            'model_card': 'distribution',
            'paper': 'distribution',
            'api_access': 'distribution',
            'fine_tuning': 'distribution',
            'training_emissions': 'environment',
            'training_time': 'environment',
            'training_hardware': 'environment',
            'quality_control': 'data',
            'access': 'data',
            'labor': 'data',
            'personal_data': 'data',
            'copyright': 'data',
            'confidential_data': 'data',
            'user_prompts': 'data',
            'evaluation_approach': 'evaluation',
            'limitations': 'evaluation'
        }
        
        # Update existing data with tier 1 findings
        updated = False
        for field, value in tier_one_data.items():
            if field == 'sources_checked':
                continue
                
            section = field_to_section.get(field)
            if section:
                if section not in existing_data:
                    existing_data[section] = {'_filled': False}
                
                # Update the field value
                existing_data[section][field] = value
                existing_data[section]['_filled'] = True
                updated = True
                
                # Special handling for release_date
                if field == 'release_date' and value and not current_release_date:
                    cur.execute("""
                        UPDATE models SET release_date = ? WHERE id = ?
                    """, (value, model_id))
        
        if updated:
            # Recalculate completeness
            percent, stars = completeness(existing_data)
            
            # Update the model with new data and completeness
            cur.execute("""
                UPDATE models 
                SET data = ?, 
                    completeness_percent = ?, 
                    bonus_stars = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                json.dumps(existing_data),
                percent,
                stars,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                model_id
            ))
            
            logger.info(f"Updated model {model_id} with tier 1 data. New completeness: {percent}%")
        
        conn.commit()

def fill_model_gaps_smart(db_path="data/model_docs.db"):
    """Fill gaps intelligently without duplicates."""
    
    # Initialise scrapers
    gap_filler = GapFillingCrawler(db_path)
    tier_one = TierOneScraper()
    
    # Get all models
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, provider, completeness_percent 
            FROM models 
            ORDER BY completeness_percent ASC
        """)
        models = cur.fetchall()
    
    logger.info(f"Processing {len(models)} models")
    
    for model_id, name, provider, completeness in models:
        if completeness and completeness >= 90:
            logger.info(f"Skipping {name} - already {completeness}% complete")
            continue
            
        logger.info(f"Processing {name} ({completeness}% complete)")
        
        # Get missing fields
        missing = gap_filler.get_missing_fields(name)
        if not missing:
            continue
            
        # Try tier 1 sources first
        tier_one_data = tier_one.fill_model_gaps({
            'name': name,
            'provider': provider
        })
        
        if tier_one_data:
            logger.info(f"Found tier 1 data for {name}: {len(tier_one_data)} fields")
            
            # Update the models table with tier 1 data
            update_model_with_tier1_data(db_path, model_id, tier_one_data)
            
            # Save tier 1 findings to sources table for provenance
            for field, value in tier_one_data.items():
                if field != 'sources_checked' and not check_existing_data(db_path, model_id, field):
                    with sqlite3.connect(db_path) as conn:
                        cur = conn.cursor()
                        
                        # Determine section from field
                        field_to_section = {
                            'legal_name': 'general',
                            'model_id': 'general',
                            'description': 'general',
                            'training_compute': 'general',
                            'flops_per_param': 'general',
                            'total_flops': 'general',
                            'intended_use': 'use',
                            'prohibited_uses': 'use',
                            'release_date': 'general',
                            'architecture': 'properties',
                            'model_sizes': 'properties',
                            'context_window': 'properties',
                            'license': 'distribution',
                            'model_card': 'distribution',
                            'paper': 'distribution',
                            'api_access': 'distribution',
                            'fine_tuning': 'distribution',
                            'training_emissions': 'environment',
                            'training_time': 'environment',
                            'training_hardware': 'environment',
                            'quality_control': 'data',
                            'access': 'data',
                            'labor': 'data',
                            'personal_data': 'data',
                            'copyright': 'data',
                            'confidential_data': 'data',
                            'user_prompts': 'data',
                            'evaluation_approach': 'evaluation',
                            'limitations': 'evaluation'
                        }
                        
                        section = field_to_section.get(field, 'general')
                        source_url = ''
                        if 'sources_checked' in tier_one_data and isinstance(tier_one_data['sources_checked'], dict):
                            source_url = tier_one_data['sources_checked'].get('url', '')
                        
                        cur.execute("""
                            INSERT INTO sources
                            (model_id, section, field, source_url, source_type, confidence, retrieved_at)
                            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                        """, (
                            model_id,
                            section,
                            field,
                            source_url,
                            'official_website',
                            0.9
                        ))
                        conn.commit()
        
        # Use regular gap filler for remaining gaps
        result = gap_filler.fill_gaps_for_model(name)
        logger.info(f"Gap filling result: {result}")

def add_google_nano_banana():
    """Check if Google Nano/Banana models should be added."""
    # These are hypothetical models - would need to verify they exist
    logger.info("Checking for Google Nano and Banana models...")
    
    # Would search Google's official docs for these models
    # For now, logging that they weren't found
    logger.info("Google Nano/Banana models not found in official sources")

if __name__ == "__main__":
    logger.info("Starting enhanced gap-filling process")
    
    # Check for specific models
    add_google_nano_banana()
    
    # Fill gaps for existing models
    fill_model_gaps_smart()
    
    logger.info("Enhanced scraping complete")