#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gap-Filling Web Scraper for GPAI Model Documentation

This module provides functionality to automatically search for and extract
missing model information from trusted sources including HuggingFace,
ArXiv, official documentation sites, and other reputable sources.

The scraper integrates with the existing database to identify gaps in
model documentation and attempts to fill them with sourced information,
tracking confidence scores based on source reliability.

Author: GPAI Documentation Pipeline
Date: November 2024
"""

import re
import time
import json
import logging
import sqlite3
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import quote, urlparse, urljoin
import sys

# Fix module imports for scripts directory
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from bs4 import BeautifulSoup

# Configure logging for proper error tracking and debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# User agent for web requests - standard browser agent to avoid blocks
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Load environment variables for API tokens
import os
from dotenv import load_dotenv
load_dotenv()

# Get HuggingFace token
HF_TOKEN = os.getenv('HF_TOKEN')

# Define trusted source types with associated confidence scores
SOURCE_CONFIDENCE = {
    "official_api": 1.0,         # Direct API responses from providers
    "official_docs": 0.95,       # Official documentation sites
    "official_newsroom": 0.9,    # Official press releases
    "huggingface": 0.85,         # HuggingFace model cards
    "arxiv": 0.8,                # ArXiv papers
    "github": 0.75,              # GitHub repositories
    "tech_news": 0.6,            # Reputable tech news sites
    "general_web": 0.4           # Other web sources
}

# Map of documentation sections to their expected fields
SECTION_FIELDS = {
    "general": ["organization", "references", "research_paper"],
    "properties": ["modality", "model_size", "dependencies", "quality_control"],
    "distribution": ["release_date", "license", "model_card", "intended_use"],
    "use": ["prohibited_uses", "monitoring", "feedback"],
    "data": ["personal_data", "copyrighted_data", "training_dataset"],
    "training": ["training_emissions", "training_time", "training_hardware"],
    "compute": ["inference_compute", "inference_time"],
    "energy": ["inference_emissions"]
}

# Trusted domains for different source types
TRUSTED_DOMAINS = {
    "huggingface": ["huggingface.co"],
    "arxiv": ["arxiv.org"],
    "official": [
        "openai.com", "anthropic.com", "google.com", "meta.com",
        "microsoft.com", "mistral.ai", "cohere.com", "ai21.com",
        "stability.ai", "01.ai", "deepmind.com"
    ],
    "tech_news": [
        "theverge.com", "techcrunch.com", "wired.com", "arstechnica.com",
        "venturebeat.com", "thenextweb.com"
    ]
}


class GapFillingCrawler:
    """
    A web crawler designed to find and fill gaps in model documentation.
    
    This crawler searches for missing information about AI models from
    trusted sources and updates the database with findings, including
    confidence scores based on source reliability.
    """
    
    def __init__(self, db_path: str = "data/model_docs.db"):
        """
        Initialise the crawler with database connection.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = Path(db_path)
        self.session = requests.Session()
        self.session.headers.update(UA)
        
        # Simple retry with backoff for rate limits
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry = Retry(total=3, backoff_factor=1)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        
        # Rate limiting between requests
        self.last_request_time = 0
        
        # Cache for scraped terms to avoid re-fetching
        self.terms_cache = {}
        
    def _safe_get(self, url: str, timeout: int = 30, headers: dict = None) -> Optional[requests.Response]:
        """Make a rate-limited GET request."""
        try:
            # Wait between requests
            elapsed = time.time() - self.last_request_time
            if elapsed < 1.5:
                time.sleep(1.5 - elapsed)
            
            self.last_request_time = time.time()
            
            # Use provided headers or default session headers
            req_headers = headers if headers else None
            
            response = self.session.get(url, timeout=timeout, headers=req_headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None
        
    def get_missing_fields(self, model_name: str) -> Dict[str, List[str]]:
        """
        Identify which fields are missing for a given model.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            Dictionary mapping sections to lists of missing fields
        """
        missing = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT data, section_data FROM models WHERE name = ?",
                (model_name,)
            )
            row = cur.fetchone()
            
            if not row:
                logger.warning(f"Model '{model_name}' not found in database")
                return missing
            
            data = json.loads(row[0] or "{}")
            section_data = json.loads(row[1] or "{}")
            
            # Check each section for missing fields
            for section, fields in SECTION_FIELDS.items():
                missing_fields = []
                for field in fields:
                    # Check if field exists and has meaningful content
                    field_data = data.get(section, {}).get(field, "")
                    if not field_data or field_data == "Not specified":
                        missing_fields.append(field)
                
                if missing_fields:
                    missing[section] = missing_fields
        
        return missing
    
    def get_first_commit_date(self, model_id: str) -> Optional[str]:
        """Get first commit date by scraping the HF files page."""
        try:
            # Try direct web scraping of the commits page
            commits_url = f"https://huggingface.co/{model_id}/commits/main"
            response = self._safe_get(commits_url)
            
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all commit entries
                commit_entries = soup.find_all('li', {'class': 'commit'})
                if not commit_entries:
                    # Try alternative structure
                    commit_entries = soup.find_all('div', {'class': 'commit-item'})
                
                # Get the last (oldest) commit date
                if commit_entries:
                    last_commit = commit_entries[-1]
                    time_elem = last_commit.find('time')
                    if time_elem and time_elem.get('datetime'):
                        return time_elem['datetime'].split('T')[0]
                
                # Fallback: check files page for dates
                files_url = f"https://huggingface.co/{model_id}/tree/main"
                response = self._safe_get(files_url)
                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Look for any time elements
                    time_elements = soup.find_all('time')
                    if time_elements:
                        dates = []
                        for elem in time_elements:
                            if elem.get('datetime'):
                                dates.append(elem['datetime'].split('T')[0])
                        if dates:
                            return min(dates)  # Return earliest date
                            
        except Exception as e:
            logger.debug(f"Could not get first commit date for {model_id}: {e}")
        
        return None
    
    def search_huggingface(self, model_name: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Search for model information on HuggingFace.
        
        Args:
            model_name: Name of the model
            provider: Model provider/organisation
            
        Returns:
            Dictionary of extracted information or None
        """
        try:
            # Fix provider names for HuggingFace
            hf_provider = provider.lower()
            if hf_provider == "mistral ai":
                hf_provider = "mistralai"
            elif hf_provider == "cohere":
                hf_provider = "Cohere"  # Fixed: Use Cohere, not CohereForAI
            elif hf_provider == "google":
                hf_provider = "google"  # Google has HF presence
            
            # Search HuggingFace first to find actual model IDs
            search_url = f"https://huggingface.co/models?search={model_name.replace(' ', '+')}"
            logger.info(f"Searching HuggingFace for: {model_name}")
            
            # Try common HuggingFace URL patterns
            potential_ids = [
                f"{hf_provider}/{model_name.lower().replace(' ', '-')}",
                f"{hf_provider}/{model_name.lower().replace(' ', '_')}",
                model_name.lower().replace(' ', '-'),
                # Specific known mappings for actual HF models
                "mistralai/Mistral-7B-v0.1" if "mistral 7b" in model_name.lower() else None,
                "mistralai/Mistral-7B-Instruct-v0.2" if "mistral 7b" in model_name.lower() else None,
                "mistralai/Mixtral-8x7B-v0.1" if "mixtral" in model_name.lower() else None,
                "mistralai/Mixtral-8x7B-Instruct-v0.1" if "mixtral" in model_name.lower() else None,
                "mistralai/Mistral-Large-Instruct-2407" if "mistral large" in model_name.lower() else None,
                "CohereForAI/c4ai-command-r-plus" if "command-r-plus" in model_name.lower() else None,
                "CohereForAI/c4ai-command-r-v01" if "command-r" in model_name.lower() and "plus" not in model_name.lower() else None,
                # Google models on HF (not Gemini)
                "google/gemma-2b" if "gemini" in model_name.lower() and "flash" in model_name.lower() else None,
                "google/gemma-7b" if "gemini" in model_name.lower() and "pro" in model_name.lower() else None,
                "google/flan-t5-xxl" if "gemini" in model_name.lower() else None,
            ]
            
            # Remove None values
            potential_ids = [id for id in potential_ids if id]
            
            # Set up headers with HF token if available
            headers = UA.copy()
            if HF_TOKEN:
                headers['Authorization'] = f'Bearer {HF_TOKEN}'
            
            for model_id in potential_ids:
                url = f"https://huggingface.co/{model_id}"
                response = self._safe_get(url, timeout=30, headers=headers)
                
                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    return self._extract_huggingface_info(soup, url)
            
        except Exception as e:
            logger.error(f"Error searching HuggingFace for {model_name}: {e}")
        
        return None
    
    def get_hf_release_date(self, model_id: str) -> Optional[str]:
        """Get actual release date from HuggingFace model files/commits."""
        try:
            # Try to get commit history
            api_url = f"https://huggingface.co/api/models/{model_id}/commits"
            headers = UA.copy()
            if HF_TOKEN:
                headers['Authorization'] = f'Bearer {HF_TOKEN}'
            
            response = self._safe_get(api_url, headers=headers)
            if response and response.status_code == 200:
                commits = response.json()
                if commits and isinstance(commits, list):
                    # Get the oldest commit (last in list)
                    oldest_commit = commits[-1]
                    if 'date' in oldest_commit:
                        return oldest_commit['date'].split('T')[0]  # Return date only
            
            # Fallback: Check files tab for creation dates
            files_url = f"https://huggingface.co/{model_id}/tree/main"
            response = self._safe_get(files_url, headers=headers)
            if response and response.status_code == 200:
                # Parse for earliest file date
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for commit dates in the file listing
                date_elements = soup.find_all('time')
                if date_elements:
                    dates = [elem.get('datetime', '').split('T')[0] for elem in date_elements if elem.get('datetime')]
                    if dates:
                        return min(dates)  # Return earliest date
        except Exception as e:
            logger.debug(f"Could not get release date for {model_id}: {e}")
        
        return None
    
    def _extract_huggingface_info(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract model information from a HuggingFace model page.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page
            
        Returns:
            Dictionary of extracted information
        """
        info = {
            "source_url": url,
            "source_type": "huggingface",
            "data": {}
        }
        
        # Extract model ID from URL
        model_id = url.split('huggingface.co/')[-1]
        
        # Get actual release date using web scraping
        release_date = self.get_first_commit_date(model_id)
        if not release_date:
            # Fallback to API method
            release_date = self.get_hf_release_date(model_id)
        
        if release_date:
            info["data"]["release_date"] = release_date
            logger.info(f"Found release date for {model_id}: {release_date}")
        
        # Extract model card content
        model_card = soup.find('div', {'class': 'prose'})
        if model_card:
            # Look for license information
            license_elem = soup.find('a', {'href': re.compile(r'/docs/hub/model-cards#license')})
            if license_elem:
                info["data"]["license"] = license_elem.get_text(strip=True)
            
            # Extract intended use section
            for heading in model_card.find_all(['h2', 'h3']):
                heading_text = heading.get_text().lower()
                if 'intended use' in heading_text:
                    next_elem = heading.find_next_sibling()
                    if next_elem:
                        info["data"]["intended_use"] = next_elem.get_text(strip=True)[:500]
                elif 'training data' in heading_text:
                    next_elem = heading.find_next_sibling()
                    if next_elem:
                        info["data"]["training_data"] = next_elem.get_text(strip=True)[:1000]
                elif 'limitations' in heading_text or 'risks' in heading_text:
                    next_elem = heading.find_next_sibling()
                    if next_elem:
                        info["data"]["limitations"] = next_elem.get_text(strip=True)[:1000]
        
        # Extract model parameters from page
        param_patterns = [
            r'(\d+\.?\d*)\s*[Bb](?:illion)?\s*param',
            r'(\d+\.?\d*)[Bb]\s*model',
            r'parameters:\s*(\d+\.?\d*)\s*[Bb]'
        ]
        
        page_text = soup.get_text()
        for pattern in param_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                info["data"]["parameters"] = f"{match.group(1)}B"
                break
        
        # Check model tags
        tags = soup.find_all('span', {'class': 'tag'})
        for tag in tags:
            text = tag.get_text(strip=True).lower()
            if 'parameters' in text or 'params' in text:
                info["data"]["model_size"] = text
        
        return info
    
    def search_arxiv(self, model_name: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Search for research papers about the model on ArXiv.
        
        Args:
            model_name: Name of the model
            provider: Model provider/organisation
            
        Returns:
            Dictionary of extracted information or None
        """
        try:
            # Search ArXiv API
            query = f"{model_name} {provider}"
            url = f"http://export.arxiv.org/api/query?search_query=all:{quote(query)}&max_results=5"
            
            response = self._safe_get(url, timeout=30)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'xml')
                entries = soup.find_all('entry')
                
                for entry in entries:
                    title = entry.find('title').get_text(strip=True)
                    # Check if this paper is likely about our model
                    if model_name.lower() in title.lower():
                        return self._extract_arxiv_info(entry)
            
        except Exception as e:
            logger.error(f"Error searching ArXiv for {model_name}: {e}")
        
        return None
    
    def _extract_arxiv_info(self, entry) -> Dict[str, Any]:
        """
        Extract information from an ArXiv entry.
        
        Args:
            entry: BeautifulSoup entry element
            
        Returns:
            Dictionary of extracted information
        """
        info = {
            "source_type": "arxiv",
            "data": {}
        }
        
        # Extract paper URL
        link = entry.find('id')
        if link:
            info["source_url"] = link.get_text(strip=True)
            info["data"]["research_paper"] = info["source_url"]
        
        # Extract abstract for potential information
        abstract = entry.find('summary')
        if abstract:
            abstract_text = abstract.get_text(strip=True)
            # Look for model size mentions
            size_match = re.search(r'(\d+\.?\d*)\s*([BMT])\s*parameter', abstract_text, re.I)
            if size_match:
                info["data"]["model_size"] = f"{size_match.group(1)}{size_match.group(2)} parameters"
        
        return info
    
    def search_google_gemini_docs(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Search Google's Gemini API documentation."""
        try:
            # Check main Gemini docs
            docs_urls = [
                "https://ai.google.dev/gemini-api/docs/models",
                "https://ai.google.dev/gemini-api/docs",
                "https://ai.google.dev/gemini-api/docs/image-generation"  # For Nano
            ]
            
            for url in docs_urls:
                response = self._safe_get(url)
                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for model information
                    if model_name.lower() in soup.get_text().lower():
                        info = {
                            "source_url": url,
                            "source_type": "official_docs",
                            "data": {}
                        }
                        
                        # Extract model details
                        tables = soup.find_all('table')
                        for table in tables:
                            rows = table.find_all('tr')
                            for row in rows:
                                cells = row.find_all(['td', 'th'])
                                if len(cells) >= 2:
                                    key = cells[0].get_text(strip=True).lower()
                                    value = cells[1].get_text(strip=True)
                                    
                                    if 'parameter' in key or 'size' in key:
                                        info["data"]["parameters"] = value
                                    elif 'release' in key or 'date' in key:
                                        info["data"]["release_date"] = value
                                    elif 'context' in key:
                                        info["data"]["context_window"] = value
                        
                        # Look for Nano specific info
                        if 'nano' in model_name.lower() or 'banana' in model_name.lower():
                            # Extract image generation capabilities
                            if 'image-generation' in url:
                                info["data"]["capabilities"] = "Image generation"
                                info["data"]["intended_use"] = "Fast on-device image generation"
                        
                        if info["data"]:
                            return info
                            
        except Exception as e:
            logger.error(f"Error searching Google docs: {e}")
        
        return None
    
    def search_official_docs(self, model_name: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Search official documentation sites for model information.
        
        Args:
            model_name: Name of the model
            provider: Model provider/organisation
            
        Returns:
            Dictionary of extracted information or None
        """
        # For Google, use specialized Gemini docs parser
        if provider.lower() == "google":
            return self.search_google_gemini_docs(model_name)
        
        # Map providers to their documentation URLs
        provider_urls = {
            "OpenAI": "https://platform.openai.com/docs/models",
            "Anthropic": "https://docs.anthropic.com/claude/docs",
            "Meta": "https://ai.meta.com/resources/models-and-libraries",
            "Mistral AI": "https://docs.mistral.ai/models",
            "Cohere": "https://docs.cohere.com/models"
        }
        
        base_url = provider_urls.get(provider)
        if not base_url:
            return None
        
        try:
            response = self.session.get(base_url, timeout=30)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                return self._extract_official_info(soup, base_url, model_name)
            
        except Exception as e:
            logger.error(f"Error searching official docs for {model_name}: {e}")
        
        return None
    
    def _extract_official_info(self, soup: BeautifulSoup, url: str, model_name: str) -> Dict[str, Any]:
        """
        Extract model information from official documentation.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page
            model_name: Name of the model to find
            
        Returns:
            Dictionary of extracted information
        """
        info = {
            "source_url": url,
            "source_type": "official_docs",
            "data": {}
        }
        
        # Search for model-specific sections
        model_pattern = re.compile(model_name.replace(' ', r'[\s\-_]?'), re.I)
        
        # Look for release dates
        date_patterns = [
            r'released?\s+(?:on\s+)?(\w+\s+\d{1,2},?\s+\d{4})',
            r'available\s+(?:since\s+)?(\w+\s+\d{1,2},?\s+\d{4})',
            r'(\d{4}-\d{2}-\d{2})'
        ]
        
        text_content = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text_content, re.I)
            if match:
                info["data"]["release_date"] = match.group(1)
                break
        
        # Extract model capabilities
        modality_keywords = ['text', 'image', 'audio', 'video', 'multimodal']
        for keyword in modality_keywords:
            if keyword in text_content.lower():
                current_modality = info["data"].get("modality", [])
                if isinstance(current_modality, list):
                    current_modality.append(keyword)
                else:
                    current_modality = [keyword]
                info["data"]["modality"] = list(set(current_modality))
        
        return info
    
    def general_web_search(self, query: str, max_results: int = 10) -> List[str]:
        """
        Perform a general web search using DuckDuckGo.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of URLs from search results
        """
        try:
            url = f"https://duckduckgo.com/html/?q={quote(query)}"
            response = self._safe_get(url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            
            links = []
            for a in soup.select("a.result__a")[:max_results]:
                href = a.get("href")
                if href:
                    links.append(href)
            
            return links
            
        except Exception as e:
            logger.error(f"Error in web search for '{query}': {e}")
            return []
    
    def extract_from_url(self, url: str, limit: int = 6000) -> str:
        """
        Extract text content from a URL.
        
        Args:
            url: URL to extract from
            limit: Maximum character limit for extracted text
            
        Returns:
            Extracted text content
        """
        try:
            response = self._safe_get(url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text from paragraphs
            text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
            return text[:limit]
            
        except Exception as e:
            logger.error(f"Error extracting from {url}: {e}")
            return ""
    
    def determine_source_type(self, url: str) -> Tuple[str, float]:
        """
        Determine the source type and confidence score for a URL.
        
        Args:
            url: URL to classify
            
        Returns:
            Tuple of (source_type, confidence_score)
        """
        domain = urlparse(url).netloc.lower()
        
        # Check against trusted domains
        for source_type, domains in TRUSTED_DOMAINS.items():
            if any(trusted in domain for trusted in domains):
                if source_type == "official":
                    return "official_docs", SOURCE_CONFIDENCE["official_docs"]
                elif source_type == "huggingface":
                    return "huggingface", SOURCE_CONFIDENCE["huggingface"]
                elif source_type == "arxiv":
                    return "arxiv", SOURCE_CONFIDENCE["arxiv"]
                elif source_type == "tech_news":
                    return "tech_news", SOURCE_CONFIDENCE["tech_news"]
        
        # Check for GitHub
        if "github.com" in domain:
            return "github", SOURCE_CONFIDENCE["github"]
        
        # Default to general web
        return "general_web", SOURCE_CONFIDENCE["general_web"]
    
    def scrape_terms_of_use(self, url: str) -> Dict[str, str]:
        """
        Scrape terms of use or policy page for relevant content.
        
        Args:
            url: URL of terms/policy page
            
        Returns:
            Dictionary with extracted use-related content
        """
        # Check cache first
        if url in self.terms_cache:
            return self.terms_cache[url]
        
        try:
            response = self._safe_get(url)
            if not response:
                return {}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text content
            text = soup.get_text()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            
            # Look for key sections
            results = {
                "intended_use": [],
                "prohibited_uses": [],
                "monitoring": [],
                "feedback": []
            }
            
            # Keywords to look for
            keywords = {
                "intended_use": ["permitted use", "acceptable use", "you may", "designed for", 
                               "intended for", "purpose", "use cases"],
                "prohibited_uses": ["prohibited", "not permitted", "you may not", "forbidden",
                                  "not allowed", "restrictions", "must not"],
                "monitoring": ["monitor", "audit", "compliance", "review", "oversight"],
                "feedback": ["feedback", "report", "contact", "support"]
            }
            
            # Extract relevant paragraphs
            for i, line in enumerate(lines):
                lower_line = line.lower()
                
                for field, terms in keywords.items():
                    if any(term in lower_line for term in terms):
                        # Get context (current line + next 2-3 lines)
                        context = [line]
                        for j in range(1, 4):
                            if i + j < len(lines):
                                context.append(lines[i + j])
                        
                        # Join and clean
                        text_block = ' '.join(context)
                        if len(text_block.split()) > 10:  # Only include substantial content
                            results[field].append(text_block)
            
            # Consolidate results
            extracted = {}
            for field, texts in results.items():
                if texts:
                    # Take first few relevant blocks
                    combined = ' '.join(texts[:3])
                    # Limit length
                    words = combined.split()
                    if len(words) > 100:
                        combined = ' '.join(words[:100]) + '...'
                    extracted[field] = combined
            
            # Cache the result
            self.terms_cache[url] = extracted
            return extracted
            
        except Exception as e:
            logger.warning(f"Failed to scrape terms from {url}: {e}")
            return {}
    
    def save_findings(self, model_id: int, findings: Dict[str, Any], preserve_duplicates: bool = True) -> None:
        """
        Save discovered information to the database.
        
        Args:
            model_id: Database ID of the model
            findings: Dictionary of discovered information
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            
            # Save source information
            for section, data in findings.get("data", {}).items():
                for field, value in data.items():
                    if value and value != "Not specified":
                        cur.execute("""
                            INSERT INTO sources 
                            (model_id, section, field, source_url, source_type, confidence, retrieved_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            model_id,
                            section,
                            field,
                            findings.get("source_url", ""),
                            findings.get("source_type", "general_web"),
                            findings.get("confidence", 0.4),
                            datetime.now().isoformat()
                        ))
            
            conn.commit()
    
    def fill_gaps_for_model(self, model_name: str) -> Dict[str, Any]:
        """
        Attempt to fill documentation gaps for a specific model.
        
        Args:
            model_name: Name of the model to process
            
        Returns:
            Summary of gaps filled
        """
        logger.info(f"Starting gap-filling process for {model_name}")
        
        # Get model details from database
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, provider FROM models WHERE name = ?",
                (model_name,)
            )
            row = cur.fetchone()
            
            if not row:
                logger.error(f"Model '{model_name}' not found in database")
                return {"error": "Model not found"}
            
            model_id, provider = row
        
        # Identify missing fields
        missing_fields = self.get_missing_fields(model_name)
        if not missing_fields:
            logger.info(f"No gaps found for {model_name}")
            return {"message": "No gaps to fill"}
        
        logger.info(f"Found gaps in {len(missing_fields)} sections for {model_name}")
        
        filled_count = 0
        findings_summary = []
        
        # Search trusted sources in order of confidence
        search_methods = [
            ("HuggingFace", self.search_huggingface),
            ("ArXiv", self.search_arxiv),
            ("Official Docs", self.search_official_docs)
        ]
        
        for source_name, search_method in search_methods:
            logger.info(f"Searching {source_name} for {model_name}")
            result = search_method(model_name, provider)
            
            if result and result.get("data"):
                self.save_findings(model_id, result)
                filled_count += len(result["data"])
                findings_summary.append({
                    "source": source_name,
                    "fields_found": list(result["data"].keys()),
                    "url": result.get("source_url", "")
                })
        
        # Check for AUP links and scrape them for deeper content
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT data FROM models WHERE name = ?",
                (model_name,)
            )
            row = cur.fetchone()
            
            if row and row[0]:
                data = json.loads(row[0])
                
                # Look for AUP/terms links in the data
                aup_url = None
                use_data = data.get("use", {})
                if isinstance(use_data, dict):
                    aup_url = use_data.get("aup_link")
                
                # Scrape terms if URL found
                if aup_url and isinstance(aup_url, str) and aup_url.startswith("http"):
                    logger.info(f"Scraping terms of use from {aup_url}")
                    terms_content = self.scrape_terms_of_use(aup_url)
                    
                    if terms_content:
                        # Update the database with scraped content
                        for field, content in terms_content.items():
                            if content and field in ["intended_use", "prohibited_uses", "monitoring", "feedback"]:
                                # Update the use section with scraped content
                                if "use" not in data:
                                    data["use"] = {"_filled": True}
                                data["use"][field] = content
                                
                                # Track the source
                                self.save_findings(model_id, {
                                    "data": {"use": {field: content}},
                                    "source_url": aup_url,
                                    "source_type": "official_docs",
                                    "confidence": 0.9
                                })
                                filled_count += 1
                        
                        # Update model data
                        cur.execute(
                            "UPDATE models SET data = ?, updated_at = ? WHERE name = ?",
                            (json.dumps(data), time.strftime('%Y-%m-%d %H:%M:%S'), model_name)
                        )
                        conn.commit()
        
        # If still missing critical information, try general web search
        remaining_gaps = self.get_missing_fields(model_name)
        if remaining_gaps:
            critical_fields = ["release_date", "model_size", "license"]
            for field in critical_fields:
                for section, fields in remaining_gaps.items():
                    if field in fields:
                        query = f"{model_name} {provider} {field.replace('_', ' ')}"
                        urls = self.general_web_search(query, max_results=5)
                        
                        for url in urls:
                            source_type, confidence = self.determine_source_type(url)
                            if confidence >= 0.6:  # Only use reasonably trusted sources
                                text = self.extract_from_url(url)
                                # Here you would implement extraction logic for specific fields
                                # This is a simplified example
                                if field in text.lower():
                                    logger.info(f"Found potential {field} information at {url}")
        
        return {
            "model": model_name,
            "gaps_found": len(missing_fields),
            "fields_filled": filled_count,
            "sources_used": findings_summary
        }
    
    def run_gap_analysis(self) -> None:
        """
        Run gap analysis on all models in the database.
        
        This method identifies models with the lowest completeness scores
        and attempts to fill their gaps.
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            # Get models with lowest completeness first
            cur.execute("""
                SELECT name, completeness_percent 
                FROM models 
                ORDER BY completeness_percent ASC
                LIMIT 20
            """)
            
            models = cur.fetchall()
        
        logger.info(f"Running gap analysis on {len(models)} models")
        
        for model_name, completeness in models:
            logger.info(f"Processing {model_name} (completeness: {completeness}%)")
            
            try:
                result = self.fill_gaps_for_model(model_name)
                logger.info(f"Gap-filling result for {model_name}: {result}")
                
                # Rate limiting to be respectful to sources
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {model_name}: {e}")
                continue
    
    def log_scraping_metadata(self, results: Dict[str, Any]) -> None:
        """
        Log scraping session metadata to the database.
        
        Args:
            results: Summary of the scraping session
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO scraping_metadata
                (scrape_date, source_url, success, models_found, fields_filled, error_message, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                results.get("source_url", "multiple"),
                results.get("success", True),
                results.get("models_processed", 0),
                results.get("fields_filled", 0),
                results.get("error_message", ""),
                results.get("duration", 0)
            ))
            conn.commit()


if __name__ == "__main__":
    # Example usage and testing
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Gap-filling web scraper for GPAI model documentation"
    )
    parser.add_argument(
        "--model",
        help="Specific model name to fill gaps for"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run gap analysis on all models"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a test search"
    )
    
    args = parser.parse_args()
    
    crawler = GapFillingCrawler()
    
    if args.test:
        # Test basic functionality
        print("Testing web search...")
        results = crawler.general_web_search("OpenAI GPT-4 release date", 3)
        for url in results:
            print(f"  - {url}")
    
    elif args.model:
        # Fill gaps for specific model
        result = crawler.fill_gaps_for_model(args.model)
        print(json.dumps(result, indent=2))
    
    elif args.all:
        # Run full gap analysis
        start_time = time.time()
        crawler.run_gap_analysis()
        duration = time.time() - start_time
        
        # Log the session
        crawler.log_scraping_metadata({
            "success": True,
            "duration": duration
        })
        
        print(f"Gap analysis completed in {duration:.2f} seconds")
    
    else:
        # Default: show example usage
        print("Example usage:")
        print("  python crawl_general.py --test              # Test search functionality")
        print("  python crawl_general.py --model 'GPT-4'     # Fill gaps for specific model")
        print("  python crawl_general.py --all               # Run gap analysis on all models")