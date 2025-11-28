#!/usr/bin/env python3
"""
Enhanced web scraper for filling gaps from tier 1 sources.
Focuses on company websites, press releases, and official documentation.
"""
import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class TierOneScraper:
    """Scraper for official company sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AI-Model-Docs-Bot/1.0)'
        })
        
        # Company domains and their common patterns
        self.company_patterns = {
            'anthropic': {
                'domain': 'anthropic.com',
                'paths': ['/news', '/research', '/claude', '/company/press'],
                'keywords': ['Claude', 'Constitutional AI', 'model card']
            },
            'openai': {
                'domain': 'openai.com',
                'paths': ['/blog', '/research', '/api', '/gpt-4'],
                'keywords': ['GPT', 'model', 'parameters', 'training']
            },
            'google': {
                'domain': 'ai.google',
                'paths': ['/gemini', '/blog', '/research', '/discover'],
                'keywords': ['Gemini', 'PaLM', 'Bard', 'model']
            },
            'meta': {
                'domain': 'ai.meta.com',
                'paths': ['/blog', '/llama', '/research', '/tools'],
                'keywords': ['Llama', 'model', 'parameters']
            },
            'mistral': {
                'domain': 'mistral.ai',
                'paths': ['/news', '/technology', '/platform'],
                'keywords': ['Mistral', 'Mixtral', 'model']
            },
            'cohere': {
                'domain': 'cohere.com',
                'paths': ['/blog', '/research', '/models'],
                'keywords': ['Command', 'Embed', 'Rerank']
            }
        }
        
    def find_press_releases(self, company: str, model_name: str) -> List[Dict]:
        """Find official press releases for a model."""
        results = []
        
        if company.lower() not in self.company_patterns:
            return results
            
        company_info = self.company_patterns[company.lower()]
        base_url = f"https://{company_info['domain']}"
        
        # Check press/news sections
        for path in ['/press', '/news', '/announcements', '/media-center']:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find articles mentioning the model
                    articles = soup.find_all(['article', 'div'], class_=re.compile('post|article|news-item|press-release'))
                    
                    for article in articles:
                        title = article.find(['h1', 'h2', 'h3', 'h4'])
                        if title and model_name.lower() in title.text.lower():
                            link = article.find('a', href=True)
                            if link:
                                results.append({
                                    'url': urljoin(base_url, link['href']),
                                    'title': title.text.strip(),
                                    'type': 'press_release',
                                    'source': 'company_website'
                                })
                                
            except Exception as e:
                logger.debug(f"Error checking {url}: {e}")
                
        return results
        
    def extract_technical_specs(self, company: str, model_name: str) -> Dict:
        """Extract technical specifications from company pages."""
        specs = {}
        
        if company.lower() not in self.company_patterns:
            return specs
            
        company_info = self.company_patterns[company.lower()]
        base_url = f"https://{company_info['domain']}"
        
        # Check technical documentation pages
        tech_paths = ['/docs', '/api', '/technical', '/developers', '/platform']
        tech_paths.extend(company_info.get('paths', []))
        
        for path in tech_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Extract parameters
                    param_patterns = [
                        r'(\d+\.?\d*)\s*[BbTt](?:illion)?\s*parameters',
                        r'parameters:\s*(\d+\.?\d*)\s*[BbTt]',
                        r'model\s*size:\s*(\d+\.?\d*)\s*[BbTt]'
                    ]
                    
                    for pattern in param_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            specs['parameters'] = f"{match.group(1)}B"
                            break
                    
                    # Extract training details
                    if 'trained on' in text.lower() or 'training data' in text.lower():
                        # Find surrounding context
                        sentences = text.split('.')
                        for sent in sentences:
                            if 'train' in sent.lower() and model_name.lower() in sent.lower():
                                specs['training_info'] = sent.strip()
                                break
                    
                    # Extract compute requirements
                    compute_patterns = [
                        r'(\d+)\s*TPU',
                        r'(\d+)\s*GPU\s*hours',
                        r'(\d+)\s*[Pp]eta[Ff]lops'
                    ]
                    
                    for pattern in compute_patterns:
                        match = re.search(pattern, text)
                        if match:
                            specs['compute'] = match.group(0)
                            break
                            
            except Exception as e:
                logger.debug(f"Error extracting from {url}: {e}")
                
        return specs
        
    def find_model_cards(self, company: str, model_name: str) -> Optional[str]:
        """Find official model cards or technical reports."""
        if company.lower() not in self.company_patterns:
            return None
            
        company_info = self.company_patterns[company.lower()]
        base_url = f"https://{company_info['domain']}"
        
        # Common model card locations
        card_paths = [
            f'/models/{model_name.lower().replace(" ", "-")}',
            f'/model-card/{model_name.lower().replace(" ", "-")}',
            f'/{model_name.lower().replace(" ", "-")}/model-card',
            '/research/publications',
            '/papers'
        ]
        
        for path in card_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    return url
                    
            except Exception:
                continue
                
        return None
        
    def extract_safety_info(self, company: str, model_name: str) -> Dict:
        """Extract safety and ethics information."""
        safety_info = {}
        
        if company.lower() not in self.company_patterns:
            return safety_info
            
        company_info = self.company_patterns[company.lower()]
        base_url = f"https://{company_info['domain']}"
        
        # Check safety/ethics pages
        safety_paths = ['/safety', '/ethics', '/responsibility', '/trust', '/principles']
        
        for path in safety_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text()
                    
                    # Look for model-specific safety info
                    if model_name.lower() in text.lower():
                        # Extract relevant paragraphs
                        paragraphs = soup.find_all('p')
                        for p in paragraphs:
                            if model_name.lower() in p.text.lower() and any(
                                keyword in p.text.lower() 
                                for keyword in ['safety', 'risk', 'limitation', 'harm']
                            ):
                                if 'risks' not in safety_info:
                                    safety_info['risks'] = []
                                safety_info['risks'].append(p.text.strip())
                                
            except Exception as e:
                logger.debug(f"Error checking safety info at {url}: {e}")
                
        return safety_info
        
    def scrape_investor_relations(self, company: str, model_name: str) -> List[Dict]:
        """Check investor relations for model announcements."""
        results = []
        
        # Common IR paths
        ir_paths = ['/investors', '/ir', '/investor-relations', '/financials']
        
        if company.lower() in self.company_patterns:
            base_url = f"https://{self.company_patterns[company.lower()]['domain']}"
            
            for path in ir_paths:
                try:
                    url = urljoin(base_url, path)
                    response = self.session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for earnings transcripts, SEC filings
                        links = soup.find_all('a', href=re.compile(r'earning|transcript|10-[KQ]|8-K'))
                        
                        for link in links:
                            if link.text and model_name.lower() in link.text.lower():
                                results.append({
                                    'url': urljoin(base_url, link['href']),
                                    'title': link.text.strip(),
                                    'type': 'investor_relations',
                                    'source': 'company_ir'
                                })
                                
                except Exception:
                    continue
                    
        return results
        
    def fill_model_gaps(self, model: Dict) -> Dict:
        """Main method to fill gaps for a model using tier 1 sources."""
        filled_fields = {}
        company = model.get('provider', '')
        model_name = model.get('name', '')
        
        logger.info(f"Filling gaps for {company} {model_name} from tier 1 sources")
        
        # Find press releases
        press_releases = self.find_press_releases(company, model_name)
        if press_releases:
            filled_fields['press_releases'] = press_releases
            
        # Extract technical specs
        tech_specs = self.extract_technical_specs(company, model_name)
        if tech_specs:
            filled_fields.update(tech_specs)
            
        # Find model cards
        model_card_url = self.find_model_cards(company, model_name)
        if model_card_url:
            filled_fields['model_card_url'] = model_card_url
            
        # Extract safety info
        safety_info = self.extract_safety_info(company, model_name)
        if safety_info:
            filled_fields.update(safety_info)
            
        # Check investor relations
        ir_mentions = self.scrape_investor_relations(company, model_name)
        if ir_mentions:
            filled_fields['investor_mentions'] = ir_mentions
            
        # Add source metadata
        filled_fields['sources_checked'] = {
            'tier': 1,
            'timestamp': datetime.now().isoformat(),
            'scraper': 'enhanced_tier1'
        }
        
        return filled_fields


def scrape_sitemap(domain: str) -> List[str]:
    """Scrape sitemap for all URLs."""
    sitemap_urls = []
    
    try:
        # Check common sitemap locations
        for sitemap_path in ['/sitemap.xml', '/sitemap_index.xml', '/sitemap']:
            url = f"https://{domain}{sitemap_path}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                
                # Extract all URLs
                for loc in soup.find_all('loc'):
                    sitemap_urls.append(loc.text)
                    
                break
                
    except Exception as e:
        logger.debug(f"Error parsing sitemap for {domain}: {e}")
        
    return sitemap_urls