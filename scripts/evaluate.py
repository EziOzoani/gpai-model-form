#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Quality Evaluation Module

This module evaluates the quality and completeness of scraped model documentation.
It provides metrics on source reliability, data completeness, and identifies
areas needing improvement.

Author: GPAI Documentation Pipeline
Date: November 2024
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = Path("data/model_docs.db")

# Define evaluation criteria
REQUIRED_FIELDS = {
    'general': ['legal_name', 'release_date', 'eu_release_date'],
    'properties': ['architecture', 'input_modalities', 'output_modalities'],
    'distribution': ['channels', 'license_type'],
    'use': ['aup_link', 'intended_or_restricted'],
    'data': ['types', 'obtain_select']
}

CRITICAL_FIELDS = {
    'general.legal_name': 'Provider legal identity',
    'general.release_date': 'Model release date',
    'properties.architecture': 'Technical architecture',
    'distribution.license_type': 'Licensing information',
    'use.aup_link': 'Acceptable use policy'
}


def evaluate_data_quality():
    """
    Comprehensive evaluation of scraped data quality.
    
    Analyses completeness, source reliability, and identifies gaps
    in the model documentation database.
    """
    logger.info("Starting data quality evaluation...")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all models
    cursor.execute("""
        SELECT id, name, provider, data, completeness_percent, 
               code_of_practice_signatory, provenance_url
        FROM models
    """)
    models = cursor.fetchall()
    
    # Evaluation metrics
    total_models = len(models)
    signatory_models = 0
    completeness_scores = []
    missing_critical = defaultdict(int)
    source_quality = defaultdict(list)
    
    print("\n" + "="*80)
    print("GPAI Model Documentation - Data Quality Evaluation Report")
    print("="*80 + "\n")
    
    # Analyse each model
    for model_id, name, provider, data_json, completeness, cop_signatory, prov_url in models:
        data = json.loads(data_json or "{}")
        
        # Track Code of Practice compliance
        if cop_signatory:
            signatory_models += 1
        
        completeness_scores.append(completeness)
        
        # Check critical fields
        for field_path, description in CRITICAL_FIELDS.items():
            section, field = field_path.split('.')
            if not data.get(section, {}).get(field):
                missing_critical[field_path] += 1
        
        # Analyse source reliability
        cursor.execute("""
            SELECT source_type, confidence, COUNT(*) 
            FROM sources 
            WHERE model_id = ?
            GROUP BY source_type
        """, (model_id,))
        
        for source_type, confidence, count in cursor.fetchall():
            source_quality[source_type].append((confidence, count))
    
    # Calculate statistics
    avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
    
    # Source reliability analysis
    print(f"Total Models Analysed: {total_models}")
    if total_models > 0:
        print(f"Code of Practice Signatories: {signatory_models} ({signatory_models/total_models*100:.1f}%)")
        print(f"Average Completeness: {avg_completeness:.1f}%\n")
    else:
        print("No models found in database.\n")
    
    # Completeness distribution
    print("Completeness Distribution:")
    print("-" * 40)
    ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
    for low, high in ranges:
        count = sum(1 for score in completeness_scores if low <= score < high)
        print(f"{low:3d}-{high:3d}%: {'█' * (count*2)} {count} models")
    
    # Critical fields analysis
    print("\nCritical Fields Missing:")
    print("-" * 40)
    for field_path, count in sorted(missing_critical.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_models) * 100
        description = CRITICAL_FIELDS[field_path]
        print(f"{field_path:30} {count:3d} missing ({percentage:5.1f}%) - {description}")
    
    # Source quality analysis
    print("\nSource Quality Analysis:")
    print("-" * 40)
    for source_type, confidence_data in source_quality.items():
        if confidence_data:
            avg_confidence = sum(c[0] for c in confidence_data) / len(confidence_data)
            total_fields = sum(c[1] for c in confidence_data)
            print(f"{source_type:20} Avg Confidence: {avg_confidence:.2f}, Fields: {total_fields}")
    
    # Scraping success analysis
    cursor.execute("""
        SELECT source_url, success, models_found, fields_filled, duration_seconds
        FROM scraping_metadata
        ORDER BY scrape_date DESC
        LIMIT 20
    """)
    
    print("\nRecent Scraping Performance:")
    print("-" * 80)
    print(f"{'Source':40} {'Success':8} {'Models':7} {'Fields':7} {'Time(s)':8}")
    print("-" * 80)
    
    for url, success, models, fields, duration in cursor.fetchall():
        success_str = "✓" if success else "✗"
        url_short = url[:37] + "..." if len(url) > 40 else url
        print(f"{url_short:40} {success_str:^8} {models:7d} {fields:7d} {duration:8.1f}")
    
    # Recommendations
    print("\nRecommendations:")
    print("-" * 40)
    
    # Identify providers with low completeness
    cursor.execute("""
        SELECT provider, AVG(completeness_percent) as avg_comp, COUNT(*) as model_count
        FROM models
        GROUP BY provider
        HAVING avg_comp < 60
        ORDER BY avg_comp
    """)
    
    low_completeness_providers = cursor.fetchall()
    if low_completeness_providers:
        print("1. Focus scraping efforts on these providers with low completeness:")
        for provider, avg_comp, count in low_completeness_providers:
            print(f"   - {provider}: {avg_comp:.1f}% average ({count} models)")
    
    # Check for non-signatories
    cursor.execute("""
        SELECT DISTINCT provider 
        FROM models 
        WHERE code_of_practice_signatory = 0
    """)
    non_signatories = [row[0] for row in cursor.fetchall()]
    if non_signatories:
        print(f"\n2. Non-signatories of EU AI Code of Practice: {', '.join(non_signatories)}")
        print("   Consider excluding or marking these models in the UI")
    
    # Identify unreliable sources
    print("\n3. Source Reliability Issues:")
    cursor.execute("""
        SELECT source_url, COUNT(*) as attempts, 
               SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
        FROM scraping_metadata
        GROUP BY source_url
        HAVING successes < attempts * 0.5
    """)
    
    unreliable_sources = cursor.fetchall()
    for url, attempts, successes in unreliable_sources:
        success_rate = (successes / attempts) * 100
        print(f"   - {url}: {success_rate:.1f}% success rate ({attempts} attempts)")
    
    conn.close()
    
    print("\n" + "="*80)
    print("Evaluation complete. Check logs for detailed information.")
    print("="*80)


def generate_quality_report() -> Dict:
    """
    Generate a structured quality report for export.
    
    Returns:
        dict: Quality metrics suitable for JSON export
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Overall statistics
    cursor.execute("SELECT COUNT(*), AVG(completeness_percent) FROM models")
    total_models, avg_completeness = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM models WHERE code_of_practice_signatory = 1")
    signatory_count = cursor.fetchone()[0]
    
    # Provider breakdown
    cursor.execute("""
        SELECT provider, COUNT(*) as models, AVG(completeness_percent) as avg_comp
        FROM models
        GROUP BY provider
    """)
    provider_stats = {row[0]: {"models": row[1], "avg_completeness": row[2]} 
                     for row in cursor.fetchall()}
    
    # Source reliability
    cursor.execute("""
        SELECT source_type, AVG(confidence) as avg_conf, COUNT(*) as uses
        FROM sources
        GROUP BY source_type
    """)
    source_stats = {row[0]: {"avg_confidence": row[1], "uses": row[2]} 
                   for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "summary": {
            "total_models": total_models,
            "avg_completeness": avg_completeness,
            "signatory_count": signatory_count,
            "signatory_percentage": (signatory_count / total_models * 100) if total_models > 0 else 0
        },
        "providers": provider_stats,
        "sources": source_stats,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }


if __name__ == "__main__":
    import time
    
    # Check if database exists
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        print("Please run the crawler first to populate the database.")
        exit(1)
    
    # Run evaluation
    evaluate_data_quality()
    
    # Optionally export report
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate scraped data quality")
    parser.add_argument("--export", help="Export report to JSON file")
    args = parser.parse_args()
    
    if args.export:
        report = generate_quality_report()
        Path(args.export).write_text(json.dumps(report, indent=2))
        print(f"\nReport exported to: {args.export}")