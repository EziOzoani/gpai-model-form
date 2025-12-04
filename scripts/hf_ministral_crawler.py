#!/usr/bin/env python3
"""
Hugging Face Ministral 3 Collection Crawler

This module crawls all models from the Mistral Ministral 3 collection
on Hugging Face and extracts their model card details for transparency
documentation.

Author: GPAI Documentation Pipeline
Date: December 2024
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import logging
from datetime import datetime
from pathlib import Path
import sys
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.db import upsert_model
from scripts.ranking_calculator import calculate_completeness
from scripts.text_extraction import clean_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ministral 3 collection URL
COLLECTION_URL = "https://huggingface.co/collections/mistralai/ministral-3"

# Headers for web requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def extract_model_card_sections(readme_content):
    """
    Extract structured sections from a model card README.
    
    Maps Hugging Face model card sections to GPAI transparency sections.
    """
    sections = {
        "general": {"_filled": False},
        "properties": {"_filled": False},
        "distribution": {"_filled": False},
        "use": {"_filled": False},
        "data": {"_filled": False},
        "training": {"_filled": False},
        "compute": {"_filled": False},
        "energy": {"_filled": False}
    }
    
    if not readme_content:
        return sections
    
    # Convert to lowercase for case-insensitive matching
    content_lower = readme_content.lower()
    
    # Extract general information
    if "mistral" in content_lower:
        sections["general"]["legal_name"] = "Mistral AI"
        sections["general"]["_filled"] = True
    
    # Extract model description
    desc_match = re.search(r'#[#\s]*(?:model\s*)?(?:description|overview|introduction)(.*?)(?=\n#|\\Z)', 
                          readme_content, re.IGNORECASE | re.DOTALL)
    if desc_match:
        sections["general"]["description"] = clean_text(desc_match.group(1))
    
    # Extract properties (architecture, parameters, etc.)
    arch_patterns = [
        r'architecture[:\s]*(.*?)(?=\n)',
        r'model\s*type[:\s]*(.*?)(?=\n)',
        r'transformer.*?architecture',
        r'based on\s*(.*?)(?=\n)'
    ]
    
    for pattern in arch_patterns:
        match = re.search(pattern, readme_content, re.IGNORECASE)
        if match:
            sections["properties"]["architecture"] = clean_text(match.group(1))
            sections["properties"]["_filled"] = True
            break
    
    # Extract parameter count
    param_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:billion|B)\s*parameter', readme_content, re.IGNORECASE)
    if param_match:
        sections["properties"]["parameters"] = f"{param_match.group(1)}B"
        sections["properties"]["_filled"] = True
    
    # Extract modalities
    if any(word in content_lower for word in ['text', 'language', 'nlp']):
        sections["properties"]["input_modalities"] = "text"
        sections["properties"]["output_modalities"] = "text"
        sections["properties"]["_filled"] = True
    
    # Extract use information
    use_sections = [
        (r'#[#\s]*(?:intended\s*)?use(?:\s*cases?)?', 'intended_use'),
        (r'#[#\s]*limitations?', 'limitations'),
        (r'#[#\s]*(?:ethical\s*)?considerations?', 'ethical_considerations'),
        (r'#[#\s]*bias(?:es)?', 'bias')
    ]
    
    for pattern, field in use_sections:
        match = re.search(f'{pattern}(.*?)(?=\n#|\\Z)', readme_content, re.IGNORECASE | re.DOTALL)
        if match:
            sections["use"][field] = clean_text(match.group(1))
            sections["use"]["_filled"] = True
    
    # Extract license/distribution info
    license_match = re.search(r'license[:\s]*(.*?)(?=\n)', readme_content, re.IGNORECASE)
    if license_match:
        sections["distribution"]["license_type"] = clean_text(license_match.group(1))
        sections["distribution"]["_filled"] = True
    
    # Extract training information
    training_sections = [
        (r'#[#\s]*training(?:\s*(?:details?|procedure|process))?', 'methodology'),
        (r'training\s*data', 'dataset'),
        (r'(?:trained|fine-tuned)\s*on', 'dataset')
    ]
    
    for pattern, field in training_sections:
        match = re.search(f'{pattern}(.*?)(?=\n#|\\Z)', readme_content, re.IGNORECASE | re.DOTALL)
        if match:
            sections["training"][field] = clean_text(match.group(1))
            sections["training"]["_filled"] = True
    
    # Extract data information
    data_match = re.search(r'#[#\s]*(?:training\s*)?data(?:set)?s?(.*?)(?=\n#|\\Z)', 
                          readme_content, re.IGNORECASE | re.DOTALL)
    if data_match:
        sections["data"]["description"] = clean_text(data_match.group(1))
        sections["data"]["_filled"] = True
    
    return sections


def fetch_collection_models():
    """Fetch all models from the Ministral 3 collection."""
    logger.info(f"Fetching collection: {COLLECTION_URL}")
    
    try:
        response = requests.get(COLLECTION_URL, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        models = []
        
        # Method 1: Try to find in SVELTE_HYDRATER
        for div in soup.find_all('div', {'class': 'SVELTE_HYDRATER'}):
            if div.get('data-props'):
                try:
                    data = json.loads(div['data-props'])
                    
                    # Look for collection items
                    if 'collection' in data:
                        collection_data = data['collection']
                        
                        if 'items' in collection_data:
                            for item in collection_data['items']:
                                if item.get('item', {}).get('type') == 'model':
                                    model_id = item['item'].get('id')
                                    if model_id:
                                        models.append(model_id)
                        
                        if models:
                            return models
                        
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Fallback to parsing links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/mistralai/') and 'Ministral-3' in href:
                # Extract model ID from href (e.g., /mistralai/Ministral-3-8B-Base-2512)
                model_id = href.lstrip('/')
                if model_id not in models:
                    models.append(model_id)
        
        return models
                    
    except Exception as e:
        logger.error(f"Failed to fetch collection: {e}")
    
    return []


def scrape_model_details(model_id):
    """Scrape detailed information from a specific model page."""
    url = f"https://huggingface.co/{model_id}"
    logger.info(f"Scraping model: {model_id}")
    
    model_info = {
        "model_name": model_id.split('/')[-1],
        "provider": "Mistral AI",
        "url": url,
        "readme_content": "",
        "metadata": {}
    }
    
    try:
        # Fetch model page
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract model metadata from SVELTE_HYDRATER
        for div in soup.find_all('div', {'class': 'SVELTE_HYDRATER'}):
            if div.get('data-target') == 'ModelHeader' and div.get('data-props'):
                try:
                    data = json.loads(div['data-props'])
                    model_data = data.get('model', {})
                    
                    # Extract metadata
                    model_info['metadata'] = {
                        'created_at': model_data.get('createdAt'),
                        'last_modified': model_data.get('lastModified'),
                        'downloads': model_data.get('downloadsAllTime'),
                        'likes': model_data.get('likes'),
                        'tags': model_data.get('tags', []),
                        'pipeline_tag': model_data.get('pipelineTag'),
                        'library_name': model_data.get('libraryName')
                    }
                    
                    # Extract dates
                    created_at = model_data.get('createdAt')
                    if created_at:
                        try:
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            model_info['release_date'] = dt.strftime('%Y-%m-%d')
                        except:
                            pass
                            
                except json.JSONDecodeError:
                    pass
        
        # Fetch README content
        readme_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
        readme_response = requests.get(readme_url, headers=HEADERS)
        
        if readme_response.status_code == 200:
            model_info['readme_content'] = readme_response.text
        
        # Add delay to be respectful
        time.sleep(1)
        
    except Exception as e:
        logger.error(f"Failed to scrape {model_id}: {e}")
    
    return model_info


def process_model_to_database(model_info):
    """Process and store model information in the database."""
    
    # Extract sections from README
    sections = extract_model_card_sections(model_info.get('readme_content', ''))
    
    # Calculate completeness
    completeness_pct, bonus_stars = calculate_completeness(sections)
    
    # Prepare model record
    model_record = {
        "name": f"Mistral {model_info['model_name']}",
        "provider": "Mistral AI",
        "url": model_info['url'],
        "data": sections,
        "completeness_percent": completeness_pct,
        "bonus_stars": bonus_stars,
        "updated_at": datetime.now().isoformat(),
        "region": "EU",  # Mistral is EU-based
        "size": "Small",  # Ministral 3B models are small
        "release_date": model_info.get('release_date'),
        "metadata": model_info.get('metadata', {})
    }
    
    # Store in database
    model_id = upsert_model(model_record)
    
    logger.info(f"Stored {model_record['name']} with {completeness_pct}% completeness and {bonus_stars} stars")
    
    return model_id


def main():
    """Main function to crawl Ministral 3 collection."""
    logger.info("Starting Ministral 3 collection crawler")
    
    # Fetch all models in the collection
    model_ids = fetch_collection_models()
    
    if not model_ids:
        logger.warning("No models found in collection")
        return
    
    logger.info(f"Found {len(model_ids)} models in collection")
    
    # Process each model
    for model_id in model_ids:
        try:
            model_info = scrape_model_details(model_id)
            if model_info and model_info.get('readme_content'):
                process_model_to_database(model_info)
            else:
                logger.warning(f"No README content found for {model_id}")
        except Exception as e:
            logger.error(f"Error processing {model_id}: {e}")
            continue
    
    logger.info("Ministral 3 collection crawl completed")


if __name__ == "__main__":
    main()