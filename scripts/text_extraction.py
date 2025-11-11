#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Text Extraction and NLP Validation Module

This module provides utilities for extracting meaningful text from web pages
and validating content quality. It ensures that scraped documentation meets
minimum quality standards before being stored.

Uses simple NLP techniques to validate text length, coherence, and relevance
whilst maintaining the KISS principle.

Author: GPAI Documentation Pipeline
Date: November 2024
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

# Minimum text lengths for different field types
# Critical fields need more substantial documentation
MIN_TEXT_LENGTHS = {
    "general": {
        "legal_name": 10,      # Company/organisation name
        "model_id": 5,         # Model identifier
        "release_date": 8,     # Date format
        "description": 50      # Model description
    },
    "properties": {
        "architecture": 30,     # Technical description
        "input_modalities": 10, # List or description
        "output_modalities": 10,
        "parameters": 20        # Parameter count/range
    },
    "distribution": {
        "license_type": 10,     # License name/type
        "channels": 15,         # Distribution channels
        "terms": 50             # Terms of service
    },
    "use": {
        "aup_link": 10,         # URL or description
        "intended_use": 50,     # Intended use cases
        "restrictions": 30      # Usage restrictions
    },
    "data": {
        "types": 20,            # Data types used
        "sources": 30,          # Data sources
        "preprocessing": 50     # Processing methods
    },
    "training": {
        "methodology": 100,     # Training approach
        "hardware": 30,         # Hardware used
        "duration": 20          # Training time
    },
    "compute": {
        "flops": 10,            # Computational requirements
        "hardware_specs": 50    # Hardware specifications
    },
    "energy": {
        "consumption": 20,      # Energy usage
        "methodology": 50       # Measurement methodology
    }
}

# Common noise patterns to filter out
NOISE_PATTERNS = [
    r'^\s*$',                          # Empty or whitespace only
    r'^[^\w\s]{3,}$',                  # Only special characters
    r'^(click|tap|press|select)',      # UI instructions
    r'^(loading|please wait)',          # Loading messages
    r'cookie.*consent',                 # Cookie notices
    r'javascript.*required',            # JS warnings
    r'^\d+$',                          # Just numbers
    r'^N/A$|^n/a$|^None$',            # Explicit empty values
]

def clean_text(text: str) -> str:
    """
    Clean and normalise extracted text.
    
    Removes excessive whitespace, normalises quotes, and strips
    common web artefacts whilst preserving meaningful content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text string
    """
    if not text:
        return ""
    
    # Normalise whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove zero-width characters and other Unicode nasties
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    
    # Normalise quotes and apostrophes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Remove markdown/HTML artefacts if present
    text = re.sub(r'<[^>]+>', '', text)  # HTML tags
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # Markdown links
    
    return text.strip()

def is_noise(text: str) -> bool:
    """
    Check if text is likely noise rather than meaningful content.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be noise
    """
    clean = text.strip().lower()
    
    # Check against noise patterns
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, clean, re.IGNORECASE):
            return True
    
    # Check for very short text
    if len(clean) < 5:
        return True
    
    # Check for excessive special characters
    special_ratio = len(re.findall(r'[^\w\s]', clean)) / max(len(clean), 1)
    if special_ratio > 0.5:
        return True
    
    return False

def extract_section_text(element: Tag, section: str, field: str) -> Optional[Dict[str, str]]:
    """
    Extract text content for a specific documentation field.
    
    Attempts to extract meaningful text from an HTML element,
    validating it meets minimum quality standards.
    
    Args:
        element: BeautifulSoup element to extract from
        section: Documentation section (e.g., 'general', 'properties')
        field: Specific field within section
        
    Returns:
        Dictionary with 'text' key if valid content found, None otherwise
    """
    if not element:
        return None
    
    # Extract all text from element
    raw_text = element.get_text(separator=' ', strip=True)
    cleaned = clean_text(raw_text)
    
    # Check if it's noise
    if is_noise(cleaned):
        return None
    
    # Get minimum length for this field
    min_length = MIN_TEXT_LENGTHS.get(section, {}).get(field, 20)
    
    # Validate length
    if len(cleaned) < min_length:
        logger.debug(f"Text too short for {section}.{field}: {len(cleaned)} < {min_length}")
        return None
    
    return {"text": cleaned}

def extract_from_table_row(row: Tag, label_pattern: str) -> Optional[str]:
    """
    Extract value from a table row based on label pattern.
    
    Looks for table rows where the first cell matches the label pattern
    and returns the content of the second cell.
    
    Args:
        row: Table row element
        label_pattern: Regex pattern to match label
        
    Returns:
        Extracted text or None
    """
    cells = row.find_all(['td', 'th'])
    if len(cells) >= 2:
        label = cells[0].get_text(strip=True)
        if re.search(label_pattern, label, re.IGNORECASE):
            value = cells[1].get_text(strip=True)
            cleaned = clean_text(value)
            if not is_noise(cleaned):
                return cleaned
    return None

def extract_from_dl(dl: Tag, term_pattern: str) -> Optional[str]:
    """
    Extract value from a definition list based on term pattern.
    
    Args:
        dl: Definition list element
        term_pattern: Regex pattern to match term
        
    Returns:
        Extracted text or None
    """
    terms = dl.find_all('dt')
    for dt in terms:
        if re.search(term_pattern, dt.get_text(strip=True), re.IGNORECASE):
            dd = dt.find_next_sibling('dd')
            if dd:
                value = dd.get_text(strip=True)
                cleaned = clean_text(value)
                if not is_noise(cleaned):
                    return cleaned
    return None

def extract_list_items(element: Tag) -> List[str]:
    """
    Extract clean list items from ul/ol elements.
    
    Args:
        element: List element
        
    Returns:
        List of cleaned item texts
    """
    items = []
    for li in element.find_all('li'):
        text = clean_text(li.get_text(strip=True))
        if not is_noise(text):
            items.append(text)
    return items

def validate_and_enhance_section(section_data: Dict, section_name: str) -> Dict:
    """
    Validate section data meets minimum requirements and enhance if needed.
    
    Ensures each field has appropriate content and marks sections
    as filled only if they meet quality thresholds.
    
    Args:
        section_data: Raw section data
        section_name: Name of the section
        
    Returns:
        Enhanced section data with validation
    """
    enhanced = {}
    valid_fields = 0
    total_fields = 0
    
    for field, value in section_data.items():
        if field.startswith('_'):  # Skip metadata fields
            enhanced[field] = value
            continue
        
        total_fields += 1
        
        if isinstance(value, dict) and 'text' in value:
            text = value.get('text', '')
            min_length = MIN_TEXT_LENGTHS.get(section_name, {}).get(field, 20)
            
            if len(text) >= min_length:
                enhanced[field] = value
                valid_fields += 1
                logger.debug(f"Valid content for {section_name}.{field}: {len(text)} chars")
            else:
                logger.debug(f"Insufficient content for {section_name}.{field}: {len(text)} < {min_length}")
        elif isinstance(value, str) and not is_noise(value):
            # Convert plain strings to proper format
            min_length = MIN_TEXT_LENGTHS.get(section_name, {}).get(field, 20)
            if len(value) >= min_length:
                enhanced[field] = {"text": value}
                valid_fields += 1
    
    # Mark section as filled only if we have substantial content
    # Require at least 50% of fields to be filled with quality content
    if total_fields > 0:
        fill_ratio = valid_fields / total_fields
        enhanced['_filled'] = fill_ratio >= 0.5
    else:
        enhanced['_filled'] = False
    
    return enhanced

def extract_model_documentation(soup: BeautifulSoup, model_name: str) -> Dict[str, Dict]:
    """
    Extract comprehensive documentation for a model from a webpage.
    
    This function attempts to extract all relevant documentation fields
    from a webpage, validating content quality and ensuring minimum
    standards are met.
    
    Args:
        soup: BeautifulSoup object of the page
        model_name: Name of the model being documented
        
    Returns:
        Dictionary mapping sections to field data
    """
    documentation = {
        "general": {},
        "properties": {},
        "distribution": {},
        "use": {},
        "data": {},
        "training": {},
        "compute": {},
        "energy": {}
    }
    
    # Look for common documentation patterns
    # Many sites use headings followed by content
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
    
    for heading in headings:
        heading_text = heading.get_text(strip=True).lower()
        
        # Map heading patterns to sections
        if any(term in heading_text for term in ['overview', 'introduction', 'about']):
            content = heading.find_next_sibling()
            if content:
                text = extract_section_text(content, 'general', 'description')
                if text:
                    documentation['general']['description'] = text
        
        elif any(term in heading_text for term in ['architecture', 'model design', 'technical']):
            content = heading.find_next_sibling()
            if content:
                text = extract_section_text(content, 'properties', 'architecture')
                if text:
                    documentation['properties']['architecture'] = text
        
        elif any(term in heading_text for term in ['license', 'terms', 'usage rights']):
            content = heading.find_next_sibling()
            if content:
                text = extract_section_text(content, 'distribution', 'license_type')
                if text:
                    documentation['distribution']['license_type'] = text
        
        elif any(term in heading_text for term in ['training', 'methodology']):
            content = heading.find_next_sibling()
            if content:
                text = extract_section_text(content, 'training', 'methodology')
                if text:
                    documentation['training']['methodology'] = text
    
    # Look for tables with key-value pairs
    tables = soup.find_all('table')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            # Try to extract various fields from table rows
            if release_date := extract_from_table_row(row, r'release.*date|launched|announced'):
                documentation['general']['release_date'] = {"text": release_date}
            
            if params := extract_from_table_row(row, r'parameters?|params|size'):
                documentation['properties']['parameters'] = {"text": params}
            
            if modalities := extract_from_table_row(row, r'modalit|input.*type|supported.*data'):
                documentation['properties']['input_modalities'] = {"text": modalities}
    
    # Validate and enhance each section
    for section_name in documentation:
        documentation[section_name] = validate_and_enhance_section(
            documentation[section_name], 
            section_name
        )
    
    return documentation