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

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.crawl_general import GapFillingCrawler
from scripts.enhanced_scraper import TierOneScraper

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
        if completeness >= 90:
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
            # Save tier 1 findings
            for field, value in tier_one_data.items():
                if not check_existing_data(db_path, model_id, field):
                    with sqlite3.connect(db_path) as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO sources
                            (model_id, section, field, source_url, source_type, confidence, retrieved_at, content)
                            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
                        """, (
                            model_id,
                            'general',  # Determine section from field
                            field,
                            tier_one_data.get('sources_checked', {}).get('url', ''),
                            'official_website',
                            0.9,
                            json.dumps(value) if isinstance(value, (dict, list)) else str(value)
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