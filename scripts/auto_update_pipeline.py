#!/usr/bin/env python3
"""
Automatic update pipeline that monitors for new data and triggers cleaning/analysis
"""

import sqlite3
import json
import time
from pathlib import Path
from datetime import datetime
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutoUpdatePipeline:
    def __init__(self, 
                 original_db="data/model_docs.db",
                 cleaned_db="data/model_docs_cleaned.db",
                 threshold=5):
        """
        Initialize the auto-update pipeline
        
        Args:
            original_db: Path to the original database
            cleaned_db: Path to the cleaned database
            threshold: Number of new models to trigger update (default: 5)
        """
        self.original_db = Path(original_db)
        self.cleaned_db = Path(cleaned_db)
        self.threshold = threshold
        self.state_file = Path("data/.pipeline_state.json")
        
    def get_model_count(self, db_path):
        """Get total number of models in database"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM models")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting model count: {e}")
            return 0
    
    def load_state(self):
        """Load pipeline state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "last_update": None,
            "last_model_count": 0,
            "total_updates": 0
        }
    
    def save_state(self, state):
        """Save pipeline state"""
        self.state_file.parent.mkdir(exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def check_for_updates(self):
        """Check if update is needed"""
        state = self.load_state()
        
        # Get current model count in original database
        current_count = self.get_model_count(self.original_db)
        last_count = state.get("last_model_count", 0)
        
        # Calculate new models added
        new_models = current_count - last_count
        
        logger.info(f"Current models: {current_count}, Last processed: {last_count}, New: {new_models}")
        
        # Check if threshold is met
        if new_models >= self.threshold:
            return True, new_models
        
        # Also check if cleaned database doesn't exist
        if not self.cleaned_db.exists():
            logger.info("Cleaned database doesn't exist, triggering update")
            return True, current_count
        
        return False, new_models
    
    def run_pipeline(self):
        """Run the complete cleaning and analysis pipeline"""
        logger.info("Starting data pipeline update...")
        
        try:
            # Step 1: Clean the data
            logger.info("Step 1: Running data cleaning...")
            result = subprocess.run(
                ["python", "scripts/create_cleaned_database.py"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"Data cleaning failed: {result.stderr}")
                return False
            
            # Step 2: Run analysis
            logger.info("Step 2: Running data analysis...")
            result = subprocess.run(
                ["python", "scripts/data_analysis.py"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"Data analysis failed: {result.stderr}")
                return False
            
            # Step 3: Generate visualizations
            logger.info("Step 3: Generating visualizations...")
            result = subprocess.run(
                ["python", "scripts/generate_visualizations.py"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.error(f"Visualization generation failed: {result.stderr}")
                return False
            
            # Update state
            state = self.load_state()
            state["last_update"] = datetime.now().isoformat()
            state["last_model_count"] = self.get_model_count(self.original_db)
            state["total_updates"] = state.get("total_updates", 0) + 1
            self.save_state(state)
            
            logger.info("Pipeline update completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return False
    
    def monitor_and_update(self, check_interval=300):
        """
        Monitor for changes and update when threshold is met
        
        Args:
            check_interval: Seconds between checks (default: 5 minutes)
        """
        logger.info(f"Starting monitoring (check every {check_interval}s, threshold: {self.threshold} new models)")
        
        while True:
            try:
                needs_update, new_models = self.check_for_updates()
                
                if needs_update:
                    logger.info(f"Update triggered! {new_models} new models detected")
                    success = self.run_pipeline()
                    
                    if success:
                        logger.info("Update completed successfully")
                    else:
                        logger.error("Update failed, will retry on next check")
                else:
                    logger.info(f"No update needed ({new_models} new models, threshold: {self.threshold})")
                
                # Wait before next check
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(check_interval)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-update data pipeline")
    parser.add_argument("--threshold", type=int, default=5,
                      help="Number of new models to trigger update (default: 5)")
    parser.add_argument("--interval", type=int, default=300,
                      help="Check interval in seconds (default: 300)")
    parser.add_argument("--once", action="store_true",
                      help="Run once instead of monitoring")
    
    args = parser.parse_args()
    
    pipeline = AutoUpdatePipeline(threshold=args.threshold)
    
    if args.once:
        # Run once
        needs_update, new_models = pipeline.check_for_updates()
        if needs_update:
            logger.info(f"Running pipeline ({new_models} new models)")
            pipeline.run_pipeline()
        else:
            logger.info(f"No update needed ({new_models} new models)")
    else:
        # Monitor continuously
        pipeline.monitor_and_update(check_interval=args.interval)


if __name__ == "__main__":
    main()