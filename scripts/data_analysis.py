#!/usr/bin/env python3
"""
Data Analysis Module for GPAI Model Documentation

Performs analysis on cleaned database to generate:
- Model distribution by provider and region
- Size categorization and trends
- Transparency score calculations
- Temporal analysis (release dates)
- Section completeness metrics
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelDataAnalyzer:
    def __init__(self, db_path="data/model_docs_cleaned.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def analyze_all(self):
        """Run all analyses and return results"""
        results = {
            "summary": self.get_summary_stats(),
            "provider_distribution": self.analyze_provider_distribution(),
            "regional_distribution": self.analyze_regional_distribution(),
            "size_distribution": self.analyze_size_distribution(),
            "temporal_analysis": self.analyze_temporal_trends(),
            "transparency_scores": self.calculate_transparency_scores(),
            "section_completeness": self.analyze_section_completeness(),
            "provider_comparisons": self.compare_providers(),
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "total_models": self.get_total_models()
            }
        }
        return results
    
    def get_total_models(self):
        """Get total number of models"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM models")
        return cursor.fetchone()[0]
    
    def get_summary_stats(self):
        """Get high-level summary statistics"""
        stats = {}
        
        # Total models
        stats['total_models'] = self.get_total_models()
        
        # Unique providers
        cursor = self.conn.execute("SELECT COUNT(DISTINCT provider) FROM models")
        stats['unique_providers'] = cursor.fetchone()[0]
        
        # Models with content
        cursor = self.conn.execute("""
            SELECT COUNT(DISTINCT model_id) FROM model_content 
            WHERE description != '' OR architecture != ''
        """)
        stats['models_with_content'] = cursor.fetchone()[0]
        
        # Average fields per model
        cursor = self.conn.execute("""
            SELECT AVG(field_count) FROM (
                SELECT model_id, COUNT(*) as field_count 
                FROM section_content 
                GROUP BY model_id
            )
        """)
        result = cursor.fetchone()[0]
        stats['avg_fields_per_model'] = round(result, 2) if result else 0
        
        return stats
    
    def analyze_provider_distribution(self):
        """Analyze distribution of models by provider"""
        cursor = self.conn.execute("""
            SELECT provider, COUNT(*) as count, 
                   GROUP_CONCAT(DISTINCT region) as regions
            FROM models 
            GROUP BY provider 
            ORDER BY count DESC
        """)
        
        distribution = []
        for row in cursor:
            distribution.append({
                "provider": row['provider'],
                "count": row['count'],
                "regions": row['regions'].split(',') if row['regions'] else []
            })
        
        return distribution
    
    def analyze_regional_distribution(self):
        """Analyze distribution by region"""
        cursor = self.conn.execute("""
            SELECT region, COUNT(*) as count,
                   GROUP_CONCAT(DISTINCT provider) as providers
            FROM models 
            WHERE region IS NOT NULL AND region != ''
            GROUP BY region 
            ORDER BY count DESC
        """)
        
        distribution = []
        for row in cursor:
            distribution.append({
                "region": row['region'],
                "count": row['count'],
                "providers": row['providers'].split(',') if row['providers'] else []
            })
        
        return distribution
    
    def analyze_size_distribution(self):
        """Analyze model size distribution"""
        cursor = self.conn.execute("""
            SELECT size, COUNT(*) as count 
            FROM models 
            WHERE size IS NOT NULL AND size != 'Unknown'
            GROUP BY size 
            ORDER BY count DESC
        """)
        
        # Categorize sizes
        size_categories = defaultdict(int)
        size_details = []
        
        for row in cursor:
            size = row['size']
            count = row['count']
            size_details.append({"size": size, "count": count})
            
            # Categorize
            if 'small' in size.lower() or size.endswith('B'):
                size_categories['Small'] += count
            elif 'medium' in size.lower() or size.endswith('M'):
                size_categories['Medium'] += count
            elif 'large' in size.lower() or 'big' in size.lower():
                size_categories['Large'] += count
            else:
                size_categories['Unknown'] += count
        
        return {
            "detailed": size_details,
            "categories": dict(size_categories)
        }
    
    def analyze_temporal_trends(self):
        """Analyze release date trends"""
        cursor = self.conn.execute("""
            SELECT release_date, provider, COUNT(*) as count
            FROM models 
            WHERE release_date IS NOT NULL AND release_date != ''
            GROUP BY release_date, provider
            ORDER BY release_date
        """)
        
        # Group by year
        yearly_trends = defaultdict(lambda: defaultdict(int))
        monthly_trends = defaultdict(int)
        
        for row in cursor:
            try:
                date = row['release_date']
                if len(date) >= 4:
                    year = date[:4]
                    yearly_trends[year][row['provider']] += row['count']
                    
                if len(date) >= 7:
                    month = date[:7]
                    monthly_trends[month] += row['count']
            except:
                continue
        
        return {
            "yearly": {year: dict(providers) for year, providers in yearly_trends.items()},
            "monthly": dict(monthly_trends)
        }
    
    def calculate_transparency_scores(self):
        """Calculate transparency scores based on documentation completeness"""
        cursor = self.conn.execute("""
            SELECT m.id, m.name, m.provider,
                   COUNT(DISTINCT sc.section) as sections_filled,
                   COUNT(sc.id) as total_fields
            FROM models m
            LEFT JOIN section_content sc ON m.id = sc.model_id
            GROUP BY m.id
        """)
        
        scores = []
        for row in cursor:
            # Base score on number of sections and fields
            base_score = min(100, (row['sections_filled'] * 12.5) + (row['total_fields'] * 2))
            
            # Bonus for content quality
            content_cursor = self.conn.execute("""
                SELECT COUNT(*) as quality_fields
                FROM section_content 
                WHERE model_id = ? AND LENGTH(field_value) > 100
            """, (row['id'],))
            
            quality_fields = content_cursor.fetchone()[0]
            quality_bonus = min(20, quality_fields * 2)
            
            final_score = min(100, base_score + quality_bonus)
            
            scores.append({
                "model": row['name'],
                "provider": row['provider'],
                "transparency_score": round(final_score, 1),
                "sections_documented": row['sections_filled'],
                "total_fields": row['total_fields']
            })
        
        # Sort by score
        scores.sort(key=lambda x: x['transparency_score'], reverse=True)
        
        # Calculate provider averages
        provider_scores = defaultdict(list)
        for score in scores:
            provider_scores[score['provider']].append(score['transparency_score'])
        
        provider_averages = {
            provider: round(sum(scores) / len(scores), 1)
            for provider, scores in provider_scores.items()
        }
        
        return {
            "model_scores": scores[:20],  # Top 20
            "provider_averages": provider_averages
        }
    
    def analyze_section_completeness(self):
        """Analyze which sections are most/least documented"""
        cursor = self.conn.execute("""
            SELECT section, COUNT(DISTINCT model_id) as models_count,
                   COUNT(*) as fields_count,
                   AVG(LENGTH(field_value)) as avg_content_length
            FROM section_content
            GROUP BY section
            ORDER BY models_count DESC
        """)
        
        sections = []
        for row in cursor:
            sections.append({
                "section": row['section'],
                "models_documented": row['models_count'],
                "total_fields": row['fields_count'],
                "avg_content_length": round(row['avg_content_length'], 0) if row['avg_content_length'] else 0
            })
        
        return sections
    
    def compare_providers(self):
        """Generate provider comparison metrics"""
        providers = {}
        
        cursor = self.conn.execute("""
            SELECT m.provider,
                   COUNT(DISTINCT m.id) as model_count,
                   COUNT(DISTINCT m.region) as regions_count,
                   COUNT(DISTINCT sc.section) as avg_sections,
                   AVG(LENGTH(sc.field_value)) as avg_doc_length
            FROM models m
            LEFT JOIN section_content sc ON m.id = sc.model_id
            GROUP BY m.provider
        """)
        
        for row in cursor:
            providers[row['provider']] = {
                "model_count": row['model_count'],
                "regions": row['regions_count'],
                "documentation_coverage": round((row['avg_sections'] / 8) * 100, 1) if row['avg_sections'] else 0,
                "avg_doc_length": round(row['avg_doc_length'], 0) if row['avg_doc_length'] else 0
            }
        
        return providers
    
    def save_analysis(self, output_path="data/analysis_results.json"):
        """Run analysis and save results"""
        results = self.analyze_all()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Analysis results saved to {output_path}")
        return results
    
    def close(self):
        self.conn.close()


def main():
    analyzer = ModelDataAnalyzer()
    try:
        results = analyzer.save_analysis()
        
        # Print summary
        print("\n=== GPAI Model Data Analysis Summary ===")
        print(f"Total Models: {results['summary']['total_models']}")
        print(f"Unique Providers: {results['summary']['unique_providers']}")
        print(f"\nTop Providers:")
        for provider in results['provider_distribution'][:5]:
            print(f"  - {provider['provider']}: {provider['count']} models")
        
        print(f"\nRegional Distribution:")
        for region in results['regional_distribution'][:5]:
            print(f"  - {region['region']}: {region['count']} models")
        
        print(f"\nTransparency Leaders:")
        for model in results['transparency_scores']['model_scores'][:5]:
            print(f"  - {model['model']}: {model['transparency_score']}%")
            
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()