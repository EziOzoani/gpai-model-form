#!/usr/bin/env python3
"""
Phase 2: Blog and news scraper for AI model announcements.
Targets tech blogs, AI news sites, and company announcements.
"""
import requests
from bs4 import BeautifulSoup
import json
import logging
from datetime import datetime, timedelta
import sqlite3
from db import get_connection
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlogNewsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Target news sources
        self.news_sources = {
            'techcrunch': {
                'url': 'https://techcrunch.com/category/artificial-intelligence/',
                'selector': 'article'
            },
            'venturebeat': {
                'url': 'https://venturebeat.com/ai/',
                'selector': '.ArticleListing__item'
            },
            'theverge': {
                'url': 'https://www.theverge.com/ai-artificial-intelligence',
                'selector': 'article'
            },
            'mit_news': {
                'url': 'https://news.mit.edu/topic/artificial-intelligence2',
                'selector': '.news-article'
            },
            'arxiv_recent': {
                'url': 'https://arxiv.org/list/cs.AI/recent',
                'selector': '.list-title'
            }
        }
        
        # Model keywords to search for
        self.model_keywords = [
            'gemini', 'gpt', 'claude', 'llama', 'mistral', 'falcon',
            'palm', 'bard', 'cohere', 'anthropic', 'openai', 'meta'
        ]
    
    def scrape_article(self, url):
        """Scrape a single article for model information."""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Extract model mentions and context
            findings = []
            text_lower = text.lower()
            
            for keyword in self.model_keywords:
                if keyword in text_lower:
                    # Find context around keyword
                    pattern = rf'(.{{0,200}}\b{keyword}\b.{{0,200}})'
                    matches = re.findall(pattern, text_lower, re.I)
                    
                    for match in matches:
                        info = self.extract_model_details(match, keyword)
                        if info:
                            info['source_url'] = url
                            info['source_type'] = 'news'
                            findings.append(info)
            
            return findings
            
        except Exception as e:
            logger.error(f"Error scraping article {url}: {e}")
            return []
    
    def extract_model_details(self, text, model_keyword):
        """Extract specific details about a model from text snippet."""
        info = {'model_keyword': model_keyword}
        
        # Parameter extraction
        param_match = re.search(r'(\d+\.?\d*)\s*[bt](?:illion)?\s*param', text, re.I)
        if param_match:
            info['parameters'] = f"{param_match.group(1)}B"
        
        # Release date extraction
        date_patterns = [
            r'(?:released?|announced?|launched?)\s*(?:on|in)?\s*(\w+\s+\d+,?\s+\d{4})',
            r'(\w+\s+\d+,?\s+\d{4})'
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.I)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    # Try parsing date
                    for fmt in ['%B %d, %Y', '%B %d %Y', '%b %d, %Y']:
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
        
        # Context window
        context_match = re.search(r'(\d+)k?\s*(?:token)?\s*context', text, re.I)
        if context_match:
            info['context_window'] = f"{context_match.group(1)}k"
        
        # Performance mentions
        if 'state-of-the-art' in text or 'sota' in text:
            info['sota_claim'] = True
        
        # Multimodal capabilities
        if 'multimodal' in text or ('vision' in text and 'language' in text):
            info['multimodal'] = True
            
        return info if len(info) > 1 else None
    
    def scrape_news_source(self, source_name, source_config):
        """Scrape a news source for AI model articles."""
        logger.info(f"Scraping {source_name}...")
        
        try:
            response = self.session.get(source_config['url'], timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            articles = []
            
            # Find article links
            if source_name == 'arxiv_recent':
                # Special handling for arXiv
                for item in soup.select('.list-title'):
                    link = item.find('a', href=True)
                    if link:
                        articles.append('https://arxiv.org' + link['href'])
            else:
                # General news sites
                for article in soup.select(source_config.get('selector', 'article'))[:10]:
                    link = article.find('a', href=True)
                    if link:
                        url = link['href']
                        if not url.startswith('http'):
                            base_url = '/'.join(source_config['url'].split('/')[:3])
                            url = base_url + url
                        articles.append(url)
            
            logger.info(f"Found {len(articles)} articles from {source_name}")
            
            # Scrape articles with multi-threading
            findings = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_url = {executor.submit(self.scrape_article, url): url for url in articles}
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        article_findings = future.result()
                        findings.extend(article_findings)
                    except Exception as e:
                        logger.error(f"Error processing {url}: {e}")
            
            return findings
            
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            return []
    
    def update_model_from_findings(self, findings):
        """Update model database with findings from news/blogs."""
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = 0
        
        for finding in findings:
            # Try to match finding to existing model
            keyword = finding.get('model_keyword', '')
            
            # Query models that might match
            cursor.execute("""
                SELECT name, provider, data 
                FROM models 
                WHERE LOWER(name) LIKE ? OR LOWER(provider) LIKE ?
            """, (f'%{keyword}%', f'%{keyword}%'))
            
            matches = cursor.fetchall()
            
            for model_name, provider, data_json in matches:
                data = json.loads(data_json)
                updated = False
                
                # Update parameters if found and not present
                if 'parameters' in finding and not data.get('properties', {}).get('parameters'):
                    if 'properties' not in data:
                        data['properties'] = {}
                    data['properties']['parameters'] = finding['parameters']
                    data['properties']['_filled'] = True
                    updated = True
                    logger.info(f"Updated {model_name} parameters: {finding['parameters']}")
                
                # Update release date if found and not present
                if 'release_date' in finding and not data.get('general', {}).get('release_date'):
                    if 'general' not in data:
                        data['general'] = {}
                    data['general']['release_date'] = finding['release_date']
                    updated = True
                    logger.info(f"Updated {model_name} release date: {finding['release_date']}")
                
                # Update context window
                if 'context_window' in finding and not data.get('properties', {}).get('context_window'):
                    if 'properties' not in data:
                        data['properties'] = {}
                    data['properties']['context_window'] = finding['context_window']
                    updated = True
                    logger.info(f"Updated {model_name} context window: {finding['context_window']}")
                
                if updated:
                    cursor.execute("""
                        UPDATE models 
                        SET data = ? 
                        WHERE name = ? AND provider = ?
                    """, (json.dumps(data), model_name, provider))
                    updates += 1
        
        conn.commit()
        conn.close()
        
        return updates

def main():
    """Run blog and news scraper."""
    scraper = BlogNewsScraper()
    
    all_findings = []
    
    # Scrape each news source with multi-threading
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_source = {
            executor.submit(scraper.scrape_news_source, name, config): name 
            for name, config in scraper.news_sources.items()
        }
        
        for future in as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                findings = future.result()
                all_findings.extend(findings)
                logger.info(f"Got {len(findings)} findings from {source_name}")
            except Exception as e:
                logger.error(f"Error with {source_name}: {e}")
    
    logger.info(f"\nTotal findings: {len(all_findings)}")
    
    # Update database with findings
    updates = scraper.update_model_from_findings(all_findings)
    logger.info(f"Updated {updates} model records")

if __name__ == "__main__":
    main()