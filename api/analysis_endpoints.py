#!/usr/bin/env python3
"""
API endpoints for serving analysis and visualization data
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from pathlib import Path
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Data paths
ANALYSIS_PATH = Path("data/analysis_results.json")
VISUALIZATIONS_PATH = Path("data/visualizations.json")
CLEANED_DB_PATH = Path("data/model_docs_cleaned.db")

@app.route('/api/analysis/summary', methods=['GET'])
def get_summary():
    """Get analysis summary data"""
    try:
        with open(ANALYSIS_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data['summary'])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analysis/visualizations/<chart_name>', methods=['GET'])
def get_visualization(chart_name):
    """Get specific visualization data"""
    try:
        with open(VISUALIZATIONS_PATH, 'r') as f:
            data = json.load(f)
        
        if chart_name in data['charts']:
            return jsonify(data['charts'][chart_name])
        else:
            return jsonify({"error": "Chart not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analysis/metrics', methods=['GET'])
def get_metrics():
    """Get key metrics for dashboard"""
    try:
        with open(VISUALIZATIONS_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data['metrics'])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analysis/provider/<provider_name>', methods=['GET'])
def get_provider_analysis(provider_name):
    """Get detailed analysis for specific provider"""
    try:
        conn = sqlite3.connect(CLEANED_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get provider models
        cursor = conn.execute("""
            SELECT m.*, 
                   COUNT(DISTINCT sc.section) as sections_documented,
                   COUNT(sc.id) as total_fields
            FROM models m
            LEFT JOIN section_content sc ON m.id = sc.model_id
            WHERE m.provider = ?
            GROUP BY m.id
        """, (provider_name,))
        
        models = []
        for row in cursor:
            models.append(dict(row))
        
        # Get transparency score
        with open(ANALYSIS_PATH, 'r') as f:
            analysis = json.load(f)
        
        provider_avg = analysis['transparency_scores']['provider_averages'].get(provider_name, 0)
        
        result = {
            "provider": provider_name,
            "model_count": len(models),
            "models": models,
            "average_transparency": provider_avg,
            "last_updated": datetime.now().isoformat()
        }
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analysis/refresh', methods=['POST'])
def refresh_analysis():
    """Trigger analysis refresh"""
    try:
        # Import and run analysis
        from scripts.data_analysis import ModelDataAnalyzer
        from scripts.generate_visualizations import VisualizationGenerator
        
        # Run analysis
        analyzer = ModelDataAnalyzer()
        analyzer.save_analysis()
        analyzer.close()
        
        # Generate visualizations
        generator = VisualizationGenerator()
        generator.save_visualizations()
        
        return jsonify({
            "status": "success",
            "message": "Analysis refreshed",
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analysis/export', methods=['GET'])
def export_analysis():
    """Export analysis data in various formats"""
    format_type = request.args.get('format', 'json')
    
    try:
        with open(ANALYSIS_PATH, 'r') as f:
            data = json.load(f)
        
        if format_type == 'json':
            return jsonify(data)
        elif format_type == 'csv':
            # Convert to CSV format for key metrics
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write provider distribution
            writer.writerow(['Provider Analysis'])
            writer.writerow(['Provider', 'Model Count', 'Regions'])
            for provider in data['provider_distribution']:
                writer.writerow([
                    provider['provider'],
                    provider['count'],
                    ', '.join(provider['regions'])
                ])
            
            response = app.response_class(
                output.getvalue(),
                mimetype='text/csv',
                headers={"Content-Disposition": "attachment;filename=gpai_analysis.csv"}
            )
            return response
        else:
            return jsonify({"error": "Unsupported format"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure data files exist
    if not ANALYSIS_PATH.exists():
        print("Running initial analysis...")
        from scripts.data_analysis import ModelDataAnalyzer
        analyzer = ModelDataAnalyzer()
        analyzer.save_analysis()
        analyzer.close()
    
    if not VISUALIZATIONS_PATH.exists():
        print("Generating visualizations...")
        from scripts.generate_visualizations import VisualizationGenerator
        generator = VisualizationGenerator()
        generator.save_visualizations()
    
    print("Starting API server on http://localhost:5001")
    app.run(debug=True, port=5001)