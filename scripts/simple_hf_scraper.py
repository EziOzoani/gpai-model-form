#!/usr/bin/env python3
"""Simple HuggingFace scraper using direct web access."""
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_hf_model(model_id):
    """Scrape HuggingFace model page directly."""
    url = f"https://huggingface.co/{model_id}"
    
    # Add proper headers to avoid 401 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"Failed to fetch {url}: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find the ModelHeader component which contains the model data
    model_header = None
    for div in soup.find_all('div', {'class': 'SVELTE_HYDRATER'}):
        if div.get('data-target') == 'ModelHeader' and div.get('data-props'):
            model_header = div
            break
    
    if model_header:
        try:
            data = json.loads(model_header['data-props'])
            model_data = data.get('model', {})
            
            # Extract dates with proper handling
            created_at = model_data.get('createdAt', '')
            if created_at:
                created_at = created_at.split('T')[0]
            
            last_modified = model_data.get('lastModified', '')
            if last_modified:
                last_modified = last_modified.split('T')[0]
            
            info = {
                'model_id': model_id,
                'created_at': created_at,
                'last_modified': last_modified,
                'downloads': model_data.get('downloads', 0),
                'likes': model_data.get('likes', 0),
                'license': model_data.get('cardData', {}).get('license', ''),
                'tags': model_data.get('tags', []),
                'pipeline_tag': model_data.get('pipeline_tag', ''),
                'library': model_data.get('library_name', '')
            }
            
            # Extract parameters from safetensors info
            safetensors = model_data.get('safetensors', {})
            if safetensors:
                total_params = safetensors.get('total', 0)
                if total_params > 0:
                    # Convert to billions
                    info['parameters'] = f"{total_params / 1e9:.1f}B"
            
            logger.info(f"Successfully scraped {model_id}: created={created_at}, params={info.get('parameters', 'N/A')}")
            return info
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON data for {model_id}: {e}")
        except Exception as e:
            logger.error(f"Error processing {model_id}: {e}")
    else:
        logger.error(f"Could not find ModelHeader component for {model_id}")
    
    return None

def update_database(db_path="data/model_docs.db"):
    """Update models with HF data."""
    
    # Known model mappings
    model_mappings = {
        "Mistral Mistral 7B": "mistralai/Mistral-7B-v0.1",
        "Mistral Mixtral": "mistralai/Mixtral-8x7B-v0.1",
        "Mistral Mistral Large": "mistralai/Mistral-Large-Instruct-2407",
        "Cohere command-r-plus-04": "Cohere/c4ai-command-r-plus",
        "Cohere command-r-03": "Cohere/c4ai-command-r-v01",
    }
    
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        
        for model_name, hf_id in model_mappings.items():
            logger.info(f"Scraping {model_name} from {hf_id}")
            
            data = scrape_hf_model(hf_id)
            if data:
                # Update release date
                if data['created_at']:
                    cur.execute("""
                        UPDATE models 
                        SET release_date = ? 
                        WHERE name = ?
                    """, (data['created_at'], model_name))
                    
                # Update model size if found
                if 'parameters' in data:
                    cur.execute("""
                        SELECT id, data FROM models WHERE name = ?
                    """, (model_name,))
                    row = cur.fetchone()
                    if row:
                        model_id, existing_data = row
                        model_data = json.loads(existing_data or '{}')
                        if 'properties' not in model_data:
                            model_data['properties'] = {}
                        model_data['properties']['parameters'] = data['parameters']
                        
                        cur.execute("""
                            UPDATE models 
                            SET data = ? 
                            WHERE id = ?
                        """, (json.dumps(model_data), model_id))
                
                logger.info(f"Updated {model_name}: release_date={data.get('created_at')}, params={data.get('parameters')}")
                
        conn.commit()

def test_scraper():
    """Test the scraper with a known model."""
    test_model = "mistralai/Mistral-7B-v0.1"
    logger.info(f"Testing scraper with {test_model}")
    
    result = scrape_hf_model(test_model)
    if result:
        logger.info(f"Test successful!")
        logger.info(f"Model: {result['model_id']}")
        logger.info(f"Created: {result['created_at']}")
        logger.info(f"Last Modified: {result['last_modified']}")
        logger.info(f"Downloads: {result['downloads']}")
        logger.info(f"Likes: {result['likes']}")
        logger.info(f"Parameters: {result.get('parameters', 'N/A')}")
        logger.info(f"License: {result['license']}")
        return True
    else:
        logger.error("Test failed - no data returned")
        return False

if __name__ == "__main__":
    # Run test first
    if test_scraper():
        logger.info("\nTest passed! Now updating database...")
        update_database()
    else:
        logger.error("Test failed. Please fix the scraper before updating the database.")