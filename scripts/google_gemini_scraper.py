#!/usr/bin/env python3
"""
Google Gemini Models Scraper

This scraper:
1. Checks HuggingFace for Google models (https://huggingface.co/google)
2. Scrapes Gemini API documentation (https://ai.google.dev/gemini-api/docs)
3. Updates the database with real release dates for Gemini models
4. Specifically looks for Gemini Nano documentation
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import sqlite3
import logging
from typing import Dict, List, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleGeminiScraper:
    """Scraper for Google Gemini models from multiple sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Known Gemini model patterns
        self.gemini_models = [
            'gemini-pro',
            'gemini-ultra',
            'gemini-nano',
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-1.0-pro'
        ]
        
    def scrape_huggingface_google(self) -> List[Dict]:
        """Scrape Google's HuggingFace page for model information."""
        logger.info("Scraping HuggingFace for Google models...")
        models = []
        
        # Get list of Google models from HuggingFace
        url = "https://huggingface.co/google"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch HuggingFace Google page: {response.status_code}")
                return models
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find model cards
            model_links = soup.find_all('a', href=re.compile(r'^/google/[^/]+$'))
            
            for link in model_links:
                model_id = link.get('href', '').strip('/')
                if model_id and model_id.startswith('google/'):
                    # Check if it's a Gemini model
                    model_name = model_id.split('/')[-1].lower()
                    if 'gemini' in model_name or 'palm' in model_name:
                        logger.info(f"Found potential Gemini/PaLM model: {model_id}")
                        model_data = self.scrape_hf_model(model_id)
                        if model_data:
                            models.append(model_data)
                        time.sleep(0.5)  # Be respectful
                        
        except Exception as e:
            logger.error(f"Error scraping HuggingFace: {e}")
            
        return models
        
    def scrape_hf_model(self, model_id: str) -> Optional[Dict]:
        """Scrape individual HuggingFace model page."""
        url = f"https://huggingface.co/{model_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for the SVELTE_HYDRATER div with ModelHeader data
            for div in soup.find_all('div', {'class': 'SVELTE_HYDRATER'}):
                if div.get('data-target') == 'ModelHeader' and div.get('data-props'):
                    try:
                        data = json.loads(div['data-props'])
                        model_data = data.get('model', {})
                        
                        # Extract dates
                        created_at = model_data.get('createdAt', '')
                        if created_at:
                            created_at = created_at.split('T')[0]
                            
                        # Extract model info
                        model_name = model_id.split('/')[-1]
                        
                        # Map to Gemini model names
                        gemini_name = None
                        if 'gemini' in model_name.lower():
                            # Try to extract version
                            if '1.5' in model_name:
                                if 'flash' in model_name.lower():
                                    gemini_name = 'Gemini 1.5 Flash'
                                else:
                                    gemini_name = 'Gemini 1.5 Pro'
                            elif 'pro' in model_name.lower():
                                gemini_name = 'Gemini Pro'
                            elif 'ultra' in model_name.lower():
                                gemini_name = 'Gemini Ultra'
                            elif 'nano' in model_name.lower():
                                gemini_name = 'Gemini Nano'
                                
                        info = {
                            'model_id': model_id,
                            'name': gemini_name or model_name,
                            'created_at': created_at,
                            'downloads': model_data.get('downloads', 0),
                            'likes': model_data.get('likes', 0),
                            'tags': model_data.get('tags', []),
                            'source': 'huggingface'
                        }
                        
                        # Extract parameters if available
                        safetensors = model_data.get('safetensors', {})
                        if safetensors:
                            total_params = safetensors.get('total', 0)
                            if total_params > 0:
                                info['parameters'] = f"{total_params / 1e9:.1f}B"
                                
                        logger.info(f"Successfully scraped {model_id}: {info}")
                        return info
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON for {model_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error scraping {model_id}: {e}")
            
        return None
        
    def scrape_gemini_api_docs(self) -> List[Dict]:
        """Scrape Gemini API documentation for model information."""
        logger.info("Scraping Gemini API documentation...")
        models = []
        
        # Main documentation page
        base_url = "https://ai.google.dev/gemini-api/docs"
        
        try:
            response = self.session.get(base_url, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch Gemini API docs: {response.status_code}")
                return models
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for model information sections
            # Gemini models are often mentioned in specific patterns
            text_content = soup.get_text()
            
            # Extract release dates from documentation
            date_patterns = [
                r'(Gemini\s+(?:Pro|Ultra|Nano|1\.5\s+(?:Pro|Flash)|1\.0))[^\n]*(?:released|available|launched)[^\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\w+\s+\d{1,2},?\s+\d{4})',
                r'(\w+\s+\d{1,2},?\s+\d{4})[^\n]*(Gemini\s+(?:Pro|Ultra|Nano|1\.5\s+(?:Pro|Flash)|1\.0))',
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        if 'Gemini' in match[0]:
                            model_name = match[0].strip()
                            date_str = match[1].strip()
                        else:
                            date_str = match[0].strip()
                            model_name = match[1].strip()
                            
                        # Parse date
                        release_date = self.parse_date(date_str)
                        if release_date:
                            models.append({
                                'name': self.normalize_model_name(model_name),
                                'release_date': release_date,
                                'source': 'gemini_api_docs'
                            })
                            
            # Check specific model pages
            model_urls = [
                'models',
                'models/gemini',
                'models/gemini-pro',
                'models/gemini-1.5-pro',
                'models/gemini-1.5-flash',
                'models/gemini-nano'
            ]
            
            for path in model_urls:
                try:
                    url = f"{base_url}/{path}"
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        model_info = self.extract_model_info_from_page(response.text)
                        if model_info:
                            models.extend(model_info)
                    time.sleep(0.5)  # Be respectful
                except Exception as e:
                    logger.debug(f"Error checking {url}: {e}")
                    
        except Exception as e:
            logger.error(f"Error scraping Gemini API docs: {e}")
            
        return models
        
    def scrape_gemini_nano_docs(self) -> List[Dict]:
        """Specifically look for Gemini Nano documentation."""
        logger.info("Looking for Gemini Nano documentation...")
        models = []
        
        # Potential URLs for Gemini Nano
        nano_urls = [
            "https://ai.google.dev/edge/mediapipe/solutions/genai/llm_inference",
            "https://ai.google.dev/edge",
            "https://developers.googleblog.com/en/gemini-nano/"
        ]
        
        for url in nano_urls:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Look for Gemini Nano mentions
                    if 'gemini nano' in text.lower() or 'gemini-nano' in text.lower():
                        logger.info(f"Found Gemini Nano information at {url}")
                        
                        # Extract any dates or version information
                        nano_info = {
                            'name': 'Gemini Nano',
                            'source': 'gemini_nano_docs',
                            'url': url
                        }
                        
                        # Look for release date patterns
                        date_match = re.search(
                            r'(?:released|available|launched)[^\n]*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\w+\s+\d{1,2},?\s+\d{4})',
                            text, re.IGNORECASE
                        )
                        if date_match:
                            release_date = self.parse_date(date_match.group(1))
                            if release_date:
                                nano_info['release_date'] = release_date
                                
                        models.append(nano_info)
                        
                time.sleep(0.5)  # Be respectful
                
            except Exception as e:
                logger.debug(f"Error checking {url}: {e}")
                
        return models
        
    def extract_model_info_from_page(self, html_content: str) -> List[Dict]:
        """Extract model information from a documentation page."""
        models = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for model specifications
        # Common patterns in documentation
        spec_sections = soup.find_all(['section', 'div'], class_=re.compile('model|specification|details'))
        
        for section in spec_sections:
            text = section.get_text()
            
            # Extract model name
            name_match = re.search(r'(Gemini\s+(?:Pro|Ultra|Nano|1\.5\s+(?:Pro|Flash)|1\.0))', text, re.IGNORECASE)
            if name_match:
                model_info = {
                    'name': self.normalize_model_name(name_match.group(1)),
                    'source': 'gemini_api_docs_detailed'
                }
                
                # Look for parameters
                param_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:billion|B)\s*parameters', text, re.IGNORECASE)
                if param_match:
                    model_info['parameters'] = f"{param_match.group(1)}B"
                    
                # Look for context window
                context_match = re.search(r'(\d+)k?\s*(?:tokens?|context)', text, re.IGNORECASE)
                if context_match:
                    model_info['context_window'] = context_match.group(1)
                    
                models.append(model_info)
                
        return models
        
    def normalize_model_name(self, name: str) -> str:
        """Normalize model names for consistency."""
        name = name.strip()
        
        # Standardize naming
        replacements = {
            'gemini-pro': 'Gemini Pro',
            'gemini-ultra': 'Gemini Ultra',
            'gemini-nano': 'Gemini Nano',
            'gemini 1.5 pro': 'Gemini 1.5 Pro',
            'gemini 1.5 flash': 'Gemini 1.5 Flash',
            'gemini 1.0': 'Gemini 1.0 Pro'
        }
        
        name_lower = name.lower()
        for old, new in replacements.items():
            if old in name_lower:
                return new
                
        # Capitalize properly
        words = name.split()
        capitalized = []
        for word in words:
            if word.lower() in ['pro', 'ultra', 'nano', 'flash']:
                capitalized.append(word.capitalize())
            else:
                capitalized.append(word)
                
        return ' '.join(capitalized)
        
    def parse_date(self, date_str: str) -> Optional[str]:
        """Parse various date formats to YYYY-MM-DD."""
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%B %d, %Y',  # January 1, 2024
            '%b %d, %Y',  # Jan 1, 2024
            '%m/%d/%Y',   # 01/01/2024
            '%d/%m/%Y',   # 01/01/2024
            '%Y-%m-%d',   # 2024-01-01
            '%B %Y',      # January 2024
            '%b %Y'       # Jan 2024
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        # Try to extract just year and month
        year_month = re.search(r'(\w+)\s+(\d{4})', date_str)
        if year_month:
            try:
                month_str = year_month.group(1)
                year = year_month.group(2)
                dt = datetime.strptime(f"{month_str} 1, {year}", '%B %d, %Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    dt = datetime.strptime(f"{month_str} 1, {year}", '%b %d, %Y')
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    pass
                    
        logger.debug(f"Could not parse date: {date_str}")
        return None
        
    def update_database(self, db_path: str = "data/model_docs.db"):
        """Update the database with scraped Gemini model information."""
        logger.info("Starting database update for Google Gemini models...")
        
        # Collect all model data
        all_models = []
        
        # Scrape HuggingFace
        hf_models = self.scrape_huggingface_google()
        all_models.extend(hf_models)
        
        # Scrape Gemini API docs
        api_models = self.scrape_gemini_api_docs()
        all_models.extend(api_models)
        
        # Specifically look for Nano
        nano_models = self.scrape_gemini_nano_docs()
        all_models.extend(nano_models)
        
        # Deduplicate and merge information
        merged_models = {}
        for model in all_models:
            name = model.get('name')
            if name:
                if name not in merged_models:
                    merged_models[name] = model
                else:
                    # Merge information, preferring non-empty values
                    for key, value in model.items():
                        if value and not merged_models[name].get(key):
                            merged_models[name][key] = value
                            
        # Update database
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            for model_name, model_data in merged_models.items():
                logger.info(f"Updating {model_name}: {model_data}")
                
                # Check if model exists
                cur.execute("SELECT id, data FROM models WHERE name = ? AND provider = 'Google'", (model_name,))
                row = cur.fetchone()
                
                if row:
                    model_id, existing_data = row
                    
                    # Update release date if we found one
                    if model_data.get('release_date'):
                        cur.execute("""
                            UPDATE models 
                            SET release_date = ?, updated_at = ?
                            WHERE id = ?
                        """, (model_data['release_date'], datetime.now().isoformat(), model_id))
                        
                    # Update model data
                    existing_json = json.loads(existing_data or '{}')
                    if 'properties' not in existing_json:
                        existing_json['properties'] = {}
                        
                    # Add any new properties
                    if model_data.get('parameters'):
                        existing_json['properties']['parameters'] = model_data['parameters']
                    if model_data.get('context_window'):
                        existing_json['properties']['context_window'] = model_data['context_window']
                    if model_data.get('source'):
                        existing_json['properties']['data_source'] = model_data['source']
                        
                    cur.execute("""
                        UPDATE models 
                        SET data = ?, updated_at = ?
                        WHERE id = ?
                    """, (json.dumps(existing_json), datetime.now().isoformat(), model_id))
                    
                else:
                    # Create new model entry if it doesn't exist
                    logger.info(f"Creating new entry for {model_name}")
                    
                    model_json = {
                        'properties': {}
                    }
                    
                    if model_data.get('parameters'):
                        model_json['properties']['parameters'] = model_data['parameters']
                    if model_data.get('context_window'):
                        model_json['properties']['context_window'] = model_data['context_window']
                    if model_data.get('source'):
                        model_json['properties']['data_source'] = model_data['source']
                        
                    cur.execute("""
                        INSERT INTO models (name, provider, release_date, data, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        model_name,
                        'Google',
                        model_data.get('release_date'),
                        json.dumps(model_json),
                        datetime.now().isoformat()
                    ))
                    
            conn.commit()
            logger.info("Database update completed")
            
    def run(self):
        """Run the complete scraping process."""
        logger.info("Starting Google Gemini scraper...")
        
        try:
            self.update_database()
            logger.info("Scraping completed successfully")
            
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            raise


def main():
    """Main entry point."""
    scraper = GoogleGeminiScraper()
    scraper.run()


if __name__ == "__main__":
    main()