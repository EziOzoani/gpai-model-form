#!/usr/bin/env python3
"""
Generate visualizations from analysis data
Creates JSON data structures optimized for web visualization libraries
"""

import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VisualizationGenerator:
    def __init__(self, analysis_path="data/analysis_results.json"):
        with open(analysis_path, 'r') as f:
            self.analysis_data = json.load(f)
    
    def generate_all_visualizations(self):
        """Generate all visualization data"""
        visualizations = {
            "charts": {
                "provider_pie": self.generate_provider_pie_chart(),
                "regional_distribution": self.generate_regional_bar_chart(),
                "size_distribution": self.generate_size_donut_chart(),
                "transparency_heatmap": self.generate_transparency_heatmap(),
                "timeline": self.generate_release_timeline(),
                "provider_comparison_radar": self.generate_provider_radar(),
                "section_completeness": self.generate_section_completeness_chart()
            },
            "metrics": self.generate_key_metrics(),
            "generated_at": datetime.now().isoformat()
        }
        
        return visualizations
    
    def generate_provider_pie_chart(self):
        """Generate data for provider distribution pie chart"""
        data = []
        colors = {
            "Google": "#4285F4",
            "Mistral AI": "#FF6B6B",
            "Cohere": "#4ECDC4",
            "Meta": "#1877F2",
            "Microsoft": "#00BCF2",
            "Anthropic": "#8B5CF6",
            "OpenAI": "#10A37F"
        }
        
        for provider in self.analysis_data["provider_distribution"]:
            data.append({
                "name": provider["provider"],
                "value": provider["count"],
                "color": colors.get(provider["provider"], "#95A5A6")
            })
        
        return {
            "type": "pie",
            "data": data,
            "title": "Models by Provider",
            "responsive": True
        }
    
    def generate_regional_bar_chart(self):
        """Generate data for regional distribution bar chart"""
        data = []
        for region in self.analysis_data["regional_distribution"]:
            data.append({
                "region": region["region"],
                "count": region["count"],
                "providers": region["providers"]
            })
        
        return {
            "type": "bar",
            "data": data,
            "title": "Models by Region",
            "xAxis": "region",
            "yAxis": "count",
            "color": "#3498DB"
        }
    
    def generate_size_donut_chart(self):
        """Generate data for model size distribution"""
        categories = self.analysis_data["size_distribution"]["categories"]
        
        data = []
        colors = {
            "Small": "#2ECC71",
            "Medium": "#F39C12",
            "Large": "#E74C3C",
            "Unknown": "#95A5A6"
        }
        
        for category, count in categories.items():
            data.append({
                "name": category,
                "value": count,
                "color": colors.get(category, "#95A5A6")
            })
        
        return {
            "type": "donut",
            "data": data,
            "title": "Model Sizes",
            "innerRadius": 60,
            "outerRadius": 100
        }
    
    def generate_transparency_heatmap(self):
        """Generate heatmap data for transparency scores"""
        # Group by provider and calculate grid
        provider_models = {}
        
        for score in self.analysis_data["transparency_scores"]["model_scores"]:
            provider = score["provider"]
            if provider not in provider_models:
                provider_models[provider] = []
            
            provider_models[provider].append({
                "model": score["model"].replace(f"{provider} ", ""),
                "score": score["transparency_score"],
                "sections": score["sections_documented"]
            })
        
        # Create heatmap data
        heatmap_data = []
        y_labels = []
        
        for provider, models in provider_models.items():
            y_labels.append(provider)
            for i, model in enumerate(models):
                heatmap_data.append({
                    "x": i,
                    "y": len(y_labels) - 1,
                    "value": model["score"],
                    "model": model["model"],
                    "provider": provider
                })
        
        return {
            "type": "heatmap",
            "data": heatmap_data,
            "title": "Model Transparency Scores",
            "yLabels": y_labels,
            "colorScale": ["#FFE5E5", "#FF6B6B", "#27AE60"]
        }
    
    def generate_release_timeline(self):
        """Generate timeline visualization data"""
        timeline_data = []
        
        monthly = self.analysis_data["temporal_analysis"]["monthly"]
        
        for month, count in sorted(monthly.items()):
            timeline_data.append({
                "date": month,
                "value": count
            })
        
        return {
            "type": "line",
            "data": timeline_data,
            "title": "Model Releases Over Time",
            "xAxis": {
                "type": "time",
                "format": "%Y-%m"
            },
            "yAxis": {
                "title": "Models Released"
            }
        }
    
    def generate_provider_radar(self):
        """Generate radar chart for provider comparison"""
        comparisons = self.analysis_data["provider_comparisons"]
        
        # Normalize metrics to 0-100 scale
        max_models = max(p["model_count"] for p in comparisons.values())
        max_doc_length = max(p["avg_doc_length"] for p in comparisons.values() if p["avg_doc_length"])
        
        radar_data = []
        for provider, metrics in comparisons.items():
            radar_data.append({
                "provider": provider,
                "metrics": [
                    {"axis": "Model Count", "value": (metrics["model_count"] / max_models) * 100},
                    {"axis": "Regional Diversity", "value": metrics["regions"] * 33.3},  # 3 regions max
                    {"axis": "Documentation Coverage", "value": metrics["documentation_coverage"]},
                    {"axis": "Avg Doc Length", "value": (metrics["avg_doc_length"] / max_doc_length) * 100 if max_doc_length else 0}
                ]
            })
        
        return {
            "type": "radar",
            "data": radar_data,
            "title": "Provider Comparison",
            "axes": ["Model Count", "Regional Diversity", "Documentation Coverage", "Avg Doc Length"]
        }
    
    def generate_section_completeness_chart(self):
        """Generate section documentation completeness chart"""
        sections = self.analysis_data["section_completeness"]
        
        data = []
        for section in sections:
            data.append({
                "section": section["section"].title(),
                "documented": section["models_documented"],
                "fields": section["total_fields"],
                "avgLength": section["avg_content_length"]
            })
        
        return {
            "type": "grouped-bar",
            "data": data,
            "title": "Documentation by Section",
            "series": [
                {"key": "documented", "name": "Models Documented", "color": "#3498DB"},
                {"key": "fields", "name": "Total Fields", "color": "#2ECC71"}
            ]
        }
    
    def generate_key_metrics(self):
        """Generate key metrics for dashboard cards"""
        summary = self.analysis_data["summary"]
        transparency = self.analysis_data["transparency_scores"]["provider_averages"]
        
        # Calculate overall transparency
        overall_transparency = sum(transparency.values()) / len(transparency) if transparency else 0
        
        return {
            "total_models": {
                "value": summary["total_models"],
                "label": "Total Models",
                "icon": "database",
                "trend": None
            },
            "providers": {
                "value": summary["unique_providers"],
                "label": "AI Providers",
                "icon": "building",
                "trend": None
            },
            "documented_models": {
                "value": summary["models_with_content"],
                "label": "Documented Models",
                "icon": "file-text",
                "percentage": round((summary["models_with_content"] / summary["total_models"]) * 100, 1)
            },
            "avg_transparency": {
                "value": round(overall_transparency, 1),
                "label": "Avg Transparency Score",
                "icon": "eye",
                "unit": "%"
            }
        }
    
    def save_visualizations(self, output_path="data/visualizations.json"):
        """Generate and save all visualizations"""
        visualizations = self.generate_all_visualizations()
        
        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(visualizations, f, indent=2)
        
        logger.info(f"Visualizations saved to {output_path}")
        return visualizations


def main():
    generator = VisualizationGenerator()
    visualizations = generator.save_visualizations()
    
    print("\n=== Visualization Data Generated ===")
    print(f"Charts created: {len(visualizations['charts'])}")
    print("Chart types:")
    for chart_name, chart_data in visualizations['charts'].items():
        print(f"  - {chart_name}: {chart_data.get('type', 'custom')} chart")
    print(f"\nKey metrics: {len(visualizations['metrics'])}")
    print("\nVisualization data saved to: data/visualizations.json")


if __name__ == "__main__":
    main()