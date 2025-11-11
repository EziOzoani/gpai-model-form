#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Documentation Completeness Scoring Module

This module calculates transparency scores for AI model documentation
based on which sections have been filled in. It implements a traffic
light system (red/orange/green) to visualise completeness at a glance.

The scoring system distinguishes between required sections (contribute
to the main percentage) and bonus sections (award additional stars).

Author: GPAI Documentation Pipeline
Date: November 2024
"""

from typing import Dict, Tuple

# Define which documentation sections are mandatory for compliance
# These sections form the basis of the completeness percentage
REQUIRED = ["general", "properties", "distribution", "use", "data"]

# Additional sections that demonstrate exemplary transparency
# Completing these awards bonus stars but doesn't affect the base percentage
BONUS = ["training", "compute", "energy"]

# Equal weighting for all required sections (20% each when all 5 are present)
# This could be adjusted to give certain sections more importance
SECTION_WEIGHTS = {s: 1/len(REQUIRED) for s in REQUIRED}

# Thresholds for the traffic light visualisation system
# These determine the colour coding in the UI heatmap
TRAFFIC_THRESHOLDS = {
    "green": 0.8,   # 80% or higher: Good transparency
    "orange": 0.4,  # 40-79%: Partial transparency
    # Below 40%: Poor transparency (defaults to red)
}


def completeness(section_map: Dict) -> Tuple[int, int]:
    """
    Calculate the overall completeness score and bonus stars for a model.
    
    This function examines which documentation sections have been filled
    (indicated by the '_filled' flag) and calculates both a percentage
    score and a star rating.
    
    Args:
        section_map (dict): Dictionary mapping section names to their data.
                           Each section should have a '_filled' boolean flag.
                           Example: {
                               "general": {"_filled": True, "legal_name": "..."},
                               "properties": {"_filled": False},
                               ...
                           }
    
    Returns:
        tuple: (completeness_percent, bonus_stars)
            - completeness_percent (int): Percentage of required sections filled (0-100)
            - bonus_stars (int): Number of bonus sections completed (0-3)
    """
    # Count how many required sections have been filled
    filled = sum(1 for s in REQUIRED if section_map.get(s, {}).get("_filled"))
    
    # Calculate percentage based on required sections only
    percent = int((filled / len(REQUIRED)) * 100)
    
    # Count bonus sections separately for star awards
    stars = sum(1 for s in BONUS if section_map.get(s, {}).get("_filled"))
    
    return percent, stars


def traffic_color(score: float) -> str:
    """
    Determine the traffic light colour for a given score.
    
    Maps a numerical score (0.0-1.0) to a colour based on defined thresholds.
    This creates an intuitive visual representation of documentation quality.
    
    Args:
        score (float): Completeness score between 0.0 and 1.0
    
    Returns:
        str: Colour name ("green", "orange", or "red")
    """
    # Check thresholds in descending order
    if score >= TRAFFIC_THRESHOLDS["green"]:
        return "green"
    
    if score >= TRAFFIC_THRESHOLDS["orange"]:
        return "orange"
    
    # Default to red for poor completeness
    return "red"