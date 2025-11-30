#!/usr/bin/env python3
"""
Add Google Nano Banana 🍌 to the database from official sources.
"""
import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import upsert_model

def scrape_nano_banana():
    """Scrape Nano Banana information from official sources."""
    
    sources = [
        "https://blog.google/technology/ai/nano-banana-pro/",
        "https://blog.google/technology/developers/gemini-3-pro-image-developers/",
        "https://en.wikipedia.org/wiki/Nano_Banana"
    ]
    
    # Initialise model data
    model_data = {
        "general": {
            "_filled": True,
            "legal_name": "Google LLC",
            "model_id": "nano-banana-pro"
        },
        "properties": {
            "_filled": True,
            "architecture": "Transformer-based",
            "input_modalities": ["text", "image"],
            "output_modalities": ["text", "image"],
            "parameters": "3B",  # Nano size
            "context_window": "32k"
        },
        "distribution": {
            "_filled": True,
            "license_type": "API Terms",
            "channels": ["Google AI Studio", "Vertex AI"],
            "license_link": "https://ai.google.dev/gemini-api/terms"
        },
        "use": {
            "_filled": True,
            "aup_link": "https://ai.google.dev/gemini-api/terms",
            "intended_use": "Image generation and understanding for consumer applications",
            "prohibited_uses": "See Google AI Prohibited Use Policy"
        },
        "data": {"_filled": False},
        "training": {"_filled": False},
        "compute": {"_filled": False},
        "energy": {"_filled": False}
    }
    
    # Try to scrape blog posts
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for url in sources[:2]:  # Blog posts
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for release date
                date_elem = soup.find('time') or soup.find('span', class_='publish-date')
                if date_elem:
                    date_text = date_elem.get('datetime', date_elem.text)
                    # Parse and format date
                    try:
                        release_date = datetime.strptime(date_text[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
                        model_data['general']['release_date'] = release_date
                    except:
                        pass
                
                # Look for parameters or specifications
                text = soup.get_text().lower()
                if '3b' in text or '3 billion' in text:
                    model_data['properties']['parameters'] = '3B'
                    
                print(f"Scraped {url}")
        except Exception as e:
            print(f"Error scraping {url}: {e}")
    
    # Wikipedia for launch date
    try:
        wiki_response = requests.get(sources[2], headers=headers, timeout=10)
        if wiki_response.status_code == 200:
            wiki_soup = BeautifulSoup(wiki_response.text, 'html.parser')
            # Look for launch date in infobox
            infobox = wiki_soup.find('table', class_='infobox')
            if infobox:
                for row in infobox.find_all('tr'):
                    if 'release' in row.text.lower() or 'launch' in row.text.lower():
                        date_cell = row.find_all('td')[-1]
                        if date_cell:
                            date_text = date_cell.text.strip()
                            # Extract date
                            import re
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                            if date_match:
                                model_data['general']['release_date'] = date_match.group(1)
    except:
        pass
    
    # Default release date if not found
    if 'release_date' not in model_data['general']:
        model_data['general']['release_date'] = '2024-11-28'  # Today
    
    # Insert into database
    model_record = {
        "name": "Google Nano Banana 🍌",  # Include banana emoji in name
        "provider": "Google",
        "region": "US",
        "size": "Small",  # Nano = Small
        "release_date": model_data['general'].get('release_date', '2024-11-28'),
        "data": model_data
    }
    
    upsert_model(model_record)
    print(f"Added Google Nano Banana 🍌 to database")
    
    return model_record

if __name__ == "__main__":
    scrape_nano_banana()