#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Centralised Ranking Calculation Module

This module provides a single source of truth for calculating transparency
scores and rankings for AI model documentation. It consolidates previously
scattered calculation logic into clean, reusable functions.

PERCENTAGE CALCULATION METHODS:
================================

1. COMPLETENESS PERCENTAGE (True Average Method)
   - Based on ALL sections filled (including star sections)
   - Formula: (filled_sections / total_sections) × 100
   - Total sections: 8 (5 core + 3 star sections)
   - Example: 6 filled out of 8 total = 75%
   - Used for: Accurate documentation completeness

2. TRANSPARENCY SCORE (Weighted Method)
   - Combines section count and field count
   - Base formula: (sections × 12.5) + (fields × 2)
   - Each section contributes 12.5% (8 sections = 100% max)
   - Each field contributes 2% (50 fields = 100% max)
   - Optional quality bonus: +2% per field with >100 characters
   - Final score capped at 100%
   - Used for: Comprehensive transparency assessment

3. BONUS STARS (Achievement System)
   - Count of optional sections filled (training, compute, energy)
   - Not included in percentage calculations
   - Range: 0-3 stars
   - Used for: Recognising exemplary documentation

4. TRAFFIC LIGHT COLOURS
   - Green: ≥80% (Excellent transparency)
   - Orange: 40-79% (Partial transparency)
   - Red: <40% (Poor transparency)
   - Used for: Visual dashboard indicators

Author: GPAI Documentation Pipeline
Date: December 2024
"""

from typing import Dict, Tuple, Optional


# Core sections for documentation
REQUIRED_SECTIONS = ["general", "properties", "distribution", "use", "data"]

# Bonus sections that award stars (⭐)
BONUS_SECTIONS = ["training", "compute", "energy"]  # Each awards one star when filled

# All sections for percentage calculation
ALL_SECTIONS = REQUIRED_SECTIONS + BONUS_SECTIONS

# Scoring weights and thresholds
SECTION_WEIGHT = 12.5  # Each section contributes 12.5% to base score
FIELD_WEIGHT = 2.0     # Each field contributes 2% to base score
MAX_SCORE = 100        # Maximum possible score
QUALITY_THRESHOLD = 100  # Minimum characters for quality bonus


class RankingCalculator:
    """Centralized ranking and scoring calculations for model transparency."""
    
    @staticmethod
    def calculate_completeness_percentage(sections_filled: Dict[str, bool]) -> int:
        """
        Calculate percentage of ALL sections filled (including star sections).
        
        This gives the true completeness percentage where:
        - 8 sections total (5 required + 3 bonus)
        - Each section = 12.5% of the total
        - Example: 6/8 sections filled = 75%
        
        Args:
            sections_filled: Dict mapping section names to filled status
            
        Returns:
            Percentage of all sections filled (0-100)
        """
        filled_count = sum(
            1 for section in ALL_SECTIONS 
            if sections_filled.get(section, False)
        )
        return int((filled_count / len(ALL_SECTIONS)) * 100)
    
    @staticmethod
    def calculate_transparency_score(
        sections_count: int,
        fields_count: int,
        quality_fields_count: Optional[int] = None
    ) -> float:
        """
        Calculate comprehensive transparency score based on sections and fields.
        
        Args:
            sections_count: Number of sections with content
            fields_count: Total number of fields filled
            quality_fields_count: Number of fields with quality content (>100 chars)
            
        Returns:
            Transparency score (0-100)
        """
        # Base score from sections and fields
        base_score = min(
            MAX_SCORE,
            (sections_count * SECTION_WEIGHT) + (fields_count * FIELD_WEIGHT)
        )
        
        # Optional quality bonus
        if quality_fields_count is not None:
            quality_bonus = min(20, quality_fields_count * 2)
            return min(MAX_SCORE, base_score + quality_bonus)
        
        return base_score
    
    @staticmethod
    def calculate_bonus_stars(sections_filled: Dict[str, bool]) -> int:
        """
        Calculate bonus stars based on optional sections filled.
        
        Star sections:
        - training ⭐
        - compute ⭐
        - energy ⭐
        
        Args:
            sections_filled: Dict mapping section names to filled status
            
        Returns:
            Number of bonus stars (0-3)
        """
        return sum(
            1 for section in BONUS_SECTIONS 
            if sections_filled.get(section, False)
        )
    
    @staticmethod
    def get_section_info(section_name: str) -> Dict[str, any]:
        """
        Get information about a section including whether it awards a star.
        
        Args:
            section_name: Name of the section
            
        Returns:
            Dict with is_star_section and star_label
        """
        is_star = section_name in BONUS_SECTIONS
        return {
            "is_star_section": is_star,
            "star_label": "⭐" if is_star else "",
            "section_type": "bonus" if is_star else "core"
        }
    
    @staticmethod
    def get_all_sections_info() -> Dict[str, Dict[str, any]]:
        """
        Get information about all sections for UI display.
        
        Returns:
            Dict mapping section names to their info
        """
        return {
            section: RankingCalculator.get_section_info(section)
            for section in ALL_SECTIONS
        }
    
    @staticmethod
    def get_traffic_color(score: float) -> str:
        """
        Determine traffic light color based on score.
        
        Args:
            score: Score value (0-100)
            
        Returns:
            Color string: "green", "orange", or "red"
        """
        if score >= 80:
            return "green"
        elif score >= 40:
            return "orange"
        return "red"
    
    @classmethod
    def calculate_from_section_map(cls, section_map: Dict) -> Dict[str, any]:
        """
        Calculate all metrics from a section map (legacy format).
        
        Args:
            section_map: Dict mapping section names to their data with '_filled' flags
            
        Returns:
            Dict with completeness_percent, transparency_score, bonus_stars, and color
        """
        # Extract filled status
        sections_filled = {
            section: data.get("_filled", False)
            for section, data in section_map.items()
        }
        
        # Count sections and fields
        sections_count = sum(1 for filled in sections_filled.values() if filled)
        fields_count = sum(
            len([k for k in data.keys() if not k.startswith('_')])
            for data in section_map.values()
            if isinstance(data, dict)
        )
        
        # Calculate metrics
        completeness_percent = cls.calculate_completeness_percentage(sections_filled)
        transparency_score = cls.calculate_transparency_score(sections_count, fields_count)
        bonus_stars = cls.calculate_bonus_stars(sections_filled)
        color = cls.get_traffic_color(completeness_percent)
        
        return {
            "completeness_percent": completeness_percent,
            "transparency_score": round(transparency_score, 1),
            "bonus_stars": bonus_stars,
            "traffic_color": color,
            "sections_info": cls.get_all_sections_info(),
            "star_sections": BONUS_SECTIONS
        }
    
    @classmethod
    def calculate_from_database(
        cls,
        sections_count: int,
        fields_count: int,
        quality_fields_count: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Calculate metrics from database counts.
        
        Args:
            sections_count: Number of sections with content
            fields_count: Total number of fields
            quality_fields_count: Number of quality fields (optional)
            
        Returns:
            Dict with transparency_score and color
        """
        transparency_score = cls.calculate_transparency_score(
            sections_count,
            fields_count,
            quality_fields_count
        )
        
        return {
            "transparency_score": round(transparency_score, 1),
            "traffic_color": cls.get_traffic_color(transparency_score)
        }


# Convenience functions for backward compatibility
def calculate_completeness(section_map: Dict) -> Tuple[int, int]:
    """Legacy function for calculating completeness and stars."""
    result = RankingCalculator.calculate_from_section_map(section_map)
    return result["completeness_percent"], result["bonus_stars"]


def calculate_transparency_score(
    sections_count: int,
    fields_count: int,
    quality_fields_count: Optional[int] = None
) -> float:
    """Legacy function for calculating transparency score."""
    return RankingCalculator.calculate_transparency_score(
        sections_count,
        fields_count,
        quality_fields_count
    )


# Export constants for UI usage
__all__ = [
    'RankingCalculator',
    'REQUIRED_SECTIONS',
    'BONUS_SECTIONS',
    'ALL_SECTIONS',
    'calculate_completeness',
    'calculate_transparency_score'
]