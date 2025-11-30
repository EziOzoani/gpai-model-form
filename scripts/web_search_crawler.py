#!/usr/bin/env python3
"""
Phase 2: General web search crawler for finding model information across the web.
Uses DuckDuckGo to find relevant pages about AI models.
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from urllib.parse import quote_plus, urlparse
from datetime import datetime
import sqlite3
from db import get_connection, upsert_model
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSearchCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def search_duckduckgo(self, query, num_results=10):
        """Search DuckDuckGo and return URLs."""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        try:
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Find result links
            for link in soup.select('.result__url'):
                url = link.get('href', '')
                if url and not url.startswith('/'):
                    if not url.startswith('http'):
                        url = 'https://' + url
                    results.append(url)
                    if len(results) >= num_results:
                        break
                        
            return results
        except Exception as e:
            logger.error(f"Error searching DuckDuckGo for '{query}': {e}")
            return []
    
    def extract_model_info(self, url, model_name):
        """Extract model information from a webpage."""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text().lower()
            
            info = {}
            
            # Look for parameters/size
            param_patterns = [
                r'(\d+\.?\d*)\s*[bt]illion\s*param',
                r'(\d+\.?\d*)[bt]\s*param',
                r'(\d+\.?\d*)\s*[bt]\s*model',
                r'parameters:\s*(\d+\.?\d*)\s*[bt]'
            ]
            for pattern in param_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    info['parameters'] = f"{match.group(1)}B"
                    break
            
            # Look for release date
            date_patterns = [
                r'released?\s*(?:on|in)?\s*(\w+\s*\d+,?\s*\d{4})',
                r'announced?\s*(?:on|in)?\s*(\w+\s*\d+,?\s*\d{4})',
                r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s*\d+,?\s*\d{4}'
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    try:
                        date_str = match.group(1) if match.lastindex else match.group(0)
                        # Parse various date formats
                        for fmt in ['%B %d, %Y', '%B %d %Y', '%b %d, %Y', '%b %d %Y']:
                            try:
                                date_obj = datetime.strptime(date_str.strip(), fmt)
                                info['release_date'] = date_obj.strftime('%Y-%m-%d')
                                break
                            except:
                                continue
                    except:
                        pass
                    if 'release_date' in info:
                        break
            
            # Look for context window
            context_patterns = [
                r'(\d+)k\s*(?:token)?\s*context',
                r'context\s*(?:window|length)?\s*(?:of|:)?\s*(\d+)k',
                r'(\d+),?(\d+)?\s*token\s*context'
            ]
            for pattern in context_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    if match.lastindex and match.lastindex > 1:
                        # Handle numbers like 32,000
                        info['context_window'] = f"{match.group(1)}{match.group(2)}"
                    else:
                        info['context_window'] = f"{match.group(1)}k"
                    break
            
            # Look for capabilities
            if 'multimodal' in text or ('vision' in text and 'language' in text):
                info['multimodal'] = True
            
            # Look for license information
            license_patterns = [
                r'license[d]?\s*under\s*([\w\s\-\.]+)',
                r'(apache\s*2\.0|mit|gpl|commercial|proprietary)',
                r'(open\s*source|closed\s*source|proprietary)'
            ]
            for pattern in license_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    info['license'] = match.group(1).strip()
                    break
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting info from {url}: {e}")
            return {}
    
    def search_model(self, model_name, provider):
        """Search for information about a specific model."""
        queries = [
            f"{model_name} {provider} parameters size",
            f"{model_name} {provider} release date announcement",
            f"{model_name} {provider} technical specifications",
            f"{model_name} {provider} model card"
        ]
        
        all_info = {}
        sources = []
        
        for query in queries:
            logger.info(f"Searching: {query}")
            urls = self.search_duckduckgo(query, num_results=5)
            
            for url in urls:
                # Skip certain domains
                domain = urlparse(url).netloc
                if any(skip in domain for skip in ['youtube.com', 'twitter.com', 'linkedin.com']):
                    continue
                    
                logger.info(f"Extracting from: {url}")
                info = self.extract_model_info(url, model_name)
                
                if info:
                    sources.append({
                        'url': url,
                        'fields_found': list(info.keys())
                    })
                    # Merge info
                    for key, value in info.items():
                        if key not in all_info:
                            all_info[key] = value
            
            # Rate limiting
            time.sleep(1)
        
        return all_info, sources

def main():
    """Run web search crawler for models with low completeness."""
    crawler = WebSearchCrawler()
    
    # Get models with low completeness
    conn = get_connection()
    cursor = conn.cursor()
    
    # Focus on models with < 50% completeness
    cursor.execute("""
        SELECT name, provider, completeness_percent, data 
        FROM models 
        WHERE completeness_percent < 50 
        ORDER BY provider, name
    """)
    
    low_completion_models = cursor.fetchall()
    logger.info(f"Found {len(low_completion_models)} models with < 50% completeness")
    
    for model_name, provider, completeness, data_json in low_completion_models:
        logger.info(f"\nSearching for {provider} {model_name} ({completeness}% complete)")
        
        # Search for model info
        info, sources = crawler.search_model(model_name, provider)
        
        if info:
            logger.info(f"Found info for {model_name}: {info}")
            
            # Update model data
            data = json.loads(data_json)
            
            # Update properties section
            if 'parameters' in info and not data.get('properties', {}).get('parameters'):
                if 'properties' not in data:
                    data['properties'] = {}
                data['properties']['parameters'] = info['parameters']
                data['properties']['_filled'] = True
                
            # Update general section  
            if 'release_date' in info and not data.get('general', {}).get('release_date'):
                if 'general' not in data:
                    data['general'] = {}
                data['general']['release_date'] = info['release_date']
                
            # Update other fields
            if 'context_window' in info:
                if 'properties' not in data:
                    data['properties'] = {}
                data['properties']['context_window'] = info['context_window']
                data['properties']['_filled'] = True
                
            if 'license' in info:
                if 'distribution' not in data:
                    data['distribution'] = {}
                data['distribution']['license_type'] = info['license']
                data['distribution']['_filled'] = True
            
            # Save updated data
            cursor.execute("""
                UPDATE models 
                SET data = ? 
                WHERE name = ? AND provider = ?
            """, (json.dumps(data), model_name, provider))
            
            # Log sources
            logger.info(f"Updated {model_name} from {len(sources)} sources")
            for source in sources:
                logger.info(f"  - {source['url']}: {', '.join(source['fields_found'])}")
                
        else:
            logger.warning(f"No additional info found for {model_name}")
        
        # Rate limiting between models
        time.sleep(2)
    
    conn.commit()
    conn.close()
    logger.info("\nWeb search crawling completed")

if __name__ == "__main__":
    main()