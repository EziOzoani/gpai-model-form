#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Management Module for GPAI Model Documentation

This module handles all SQLite database operations for storing and retrieving
AI model documentation. It provides functions for initialising the database,
and performing CRUD operations on model records.

Author: GPAI Documentation Pipeline
Date: November 2024
"""

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def get_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'scraped_not_cleaned_final.db')
    return sqlite3.connect(db_path)

# Define the path to our SQLite database
# This will be created in the data directory relative to the project root
DB_PATH = Path("data/model_docs.db")

# SQL schema definitions for our two main tables
# models: Stores core model information and metadata
# sources: Tracks provenance of each data field with confidence scores
SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS models (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      provider TEXT,
      region TEXT,
      size TEXT,
      release_date TEXT,
      data TEXT,
      completeness_percent INTEGER,
      bonus_stars INTEGER,
      label_x TEXT,
      section_data TEXT,  -- Stores full documentation text for each section as JSON
      code_of_practice_signatory BOOLEAN DEFAULT FALSE,  -- EU AI Code of Practice compliance
      provenance_url TEXT,  -- URL where model info was found
      updated_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS sources (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      model_id INTEGER,
      section TEXT,      -- Changed from 'field' to 'section' for clarity
      field TEXT,        -- Specific field within the section
      source_url TEXT,
      source_type TEXT,  -- 'official_api', 'official_newsroom', 'hf_card', etc.
      confidence REAL,
      retrieved_at TEXT,
      FOREIGN KEY(model_id) REFERENCES models(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS scraping_metadata (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      scrape_date TEXT,
      source_url TEXT,
      success BOOLEAN,
      models_found INTEGER,
      fields_filled INTEGER,
      error_message TEXT,
      duration_seconds REAL
    );
    """,
]

def connect():
    """
    Establish a connection to the SQLite database.
    
    Creates the parent directory if it doesn't exist to prevent
    file system errors when creating the database for the first time.
    
    Returns:
        sqlite3.Connection: Active database connection object
    """
    # Ensure the data directory exists before attempting to create the database
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db(silent=False):
    """
    Initialise the database with the required schema.
    
    Creates the models and sources tables if they don't already exist.
    This function is idempotent - safe to call multiple times.
    
    Args:
        silent (bool): If True, suppresses console output. Useful for
                      automated scripts and testing.
    """
    with connect() as cx:
        # Execute each CREATE TABLE statement defined in our schema
        for stmt in SCHEMA:
            cx.execute(stmt)
        cx.commit()
    
    # Provide feedback unless running in silent mode
    if not silent:
        print(f"Database initialised at {DB_PATH}")

def upsert_model(model):
    """
    Insert or update a model record in the database.
    
    This function performs an "upsert" operation - it will update an existing
    record if a model with the same name exists, or insert a new record otherwise.
    
    Args:
        model (dict): Dictionary containing model information with keys:
            - name (str): Unique model identifier
            - provider (str): Company/organisation providing the model
            - region (str): Geographic region (US, EU, Non-EU)
            - size (str): Model size category (Big, Small)
            - release_date (str): ISO format date string
            - data (dict): Nested dictionary of documentation sections
            - completeness_percent (int): Overall completeness score (0-100)
            - bonus_stars (int): Number of bonus sections completed
            - label_x (str): Combined region-size label for grouping
            - section_data (dict): Full documentation text for each section
            - code_of_practice_signatory (bool): Whether provider signed EU AI Code of Practice
            - provenance_url (str): Source URL where information was retrieved
    
    Returns:
        int: Database ID of the inserted or updated record
    """
    # Record the current timestamp for audit purposes
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    
    with connect() as cx:
        cur = cx.cursor()
        
        # Check if a model with this name already exists
        cur.execute("SELECT id FROM models WHERE name=?", (model["name"],))
        row = cur.fetchone()
        
        # Prepare the data tuple for insertion/update
        # Note: We serialise the nested 'data' dictionary as JSON
        # Prepare section_data - contains full text and source info for each section
        section_data = model.get("section_data", {})
        
        payload = (
            model["name"], 
            model.get("provider"),
            model.get("region"),
            model.get("size"),
            model.get("release_date"),
            json.dumps(model.get("data", {})),  # Serialise complex data as JSON
            model.get("completeness_percent", 0),
            model.get("bonus_stars", 0),
            model.get("label_x"),
            json.dumps(section_data),  # Serialise section documentation as JSON
            model.get("code_of_practice_signatory", False),
            model.get("provenance_url"),
            now
        )
        
        if row:
            # Model exists - perform an update
            # Note: We exclude the name from the update values and add it to WHERE
            cur.execute("""
              UPDATE models SET provider=?, region=?, size=?, release_date=?, data=?,
                completeness_percent=?, bonus_stars=?, label_x=?, section_data=?,
                code_of_practice_signatory=?, provenance_url=?, updated_at=?
              WHERE name=?
            """, payload[1:] + (model["name"],))
            model_id = row[0]
        else:
            # New model - perform an insert
            cur.execute("""
              INSERT INTO models (name, provider, region, size, release_date, data,
                completeness_percent, bonus_stars, label_x, section_data,
                code_of_practice_signatory, provenance_url, updated_at)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, payload)
            model_id = cur.lastrowid
        
        # Commit the transaction
        cx.commit()
    
    return model_id

def log_scraping_metadata(source_url, success, models_found=0, fields_filled=0, 
                         error_message=None, duration_seconds=0):
    """
    Log metadata about a scraping operation for audit and quality tracking.
    
    This function records detailed information about each scraping attempt,
    allowing us to track source reliability and identify problematic sources.
    
    Args:
        source_url (str): URL that was scraped
        success (bool): Whether scraping completed without errors
        models_found (int): Number of models discovered
        fields_filled (int): Number of fields successfully populated
        error_message (str): Error details if scraping failed
        duration_seconds (float): Time taken to complete scraping
    """
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    
    with connect() as cx:
        cur = cx.cursor()
        cur.execute("""
            INSERT INTO scraping_metadata 
            (scrape_date, source_url, success, models_found, 
             fields_filled, error_message, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (now, source_url, success, models_found, 
               fields_filled, error_message, duration_seconds))
        cx.commit()


def add_source_record(model_id, section, field, source_url, 
                      source_type, confidence=0.8):
    """
    Record the source of a specific piece of information.
    
    This maintains provenance for each data point, allowing us to
    track where information came from and its reliability.
    
    Args:
        model_id (int): Database ID of the model
        section (str): Documentation section (e.g., 'general', 'properties')
        field (str): Specific field within section
        source_url (str): Where the information was found
        source_type (str): Type of source ('official', 'research', etc.)
        confidence (float): Confidence score (0.0-1.0)
    """
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    
    with connect() as cx:
        cur = cx.cursor()
        cur.execute("""
            INSERT INTO sources 
            (model_id, section, field, source_url, source_type, 
             confidence, retrieved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (model_id, section, field, source_url, 
               source_type, confidence, now))
        cx.commit()


if __name__ == "__main__":
    # Command-line interface for database operations
    # This allows the script to be run directly for maintenance tasks
    
    # Set up argument parser for command-line options
    ap = argparse.ArgumentParser(
        description="GPAI Model Documentation Database Management",
        epilog="Example: python db.py --init --silent"
    )
    
    # Define command-line arguments
    ap.add_argument(
        "--init", 
        action="store_true",
        help="Initialise the database with required schema"
    )
    ap.add_argument(
        "--silent", 
        action="store_true",
        help="Suppress console output (useful for automated scripts)"
    )
    
    # Parse arguments and execute requested operations
    args = ap.parse_args()
    
    if args.init:
        init_db(silent=args.silent)