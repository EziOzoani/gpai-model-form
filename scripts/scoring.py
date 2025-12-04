#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Documentation Completeness Scoring Module

This module provides legacy compatibility for the scoring system.
It now delegates to the centralized ranking_calculator module.

Author: GPAI Documentation Pipeline
Date: November 2024
"""

from typing import Dict, Tuple
from ranking_calculator import RankingCalculator, REQUIRED_SECTIONS, BONUS_SECTIONS

# Legacy exports for backward compatibility
REQUIRED = REQUIRED_SECTIONS
BONUS = BONUS_SECTIONS

# Legacy thresholds
TRAFFIC_THRESHOLDS = {
    "green": 0.8,   # 80% or higher: Good transparency
    "orange": 0.4,  # 40-79%: Partial transparency
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
    
    Returns:
        tuple: (completeness_percent, bonus_stars)
    """
    result = RankingCalculator.calculate_from_section_map(section_map)
    return result["completeness_percent"], result["bonus_stars"]


def traffic_color(score: float) -> str:
    """
    Determine the traffic light colour for a given score.
    
    Args:
        score (float): Completeness score between 0.0 and 1.0
    
    Returns:
        str: Colour name ("green", "orange", or "red")
    """
    # Convert to percentage if needed
    if score <= 1.0:
        score = score * 100
    
    return RankingCalculator.get_traffic_color(score)