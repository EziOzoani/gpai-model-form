#!/usr/bin/env python3
"""
Enhanced automatic update pipeline that monitors for both new models and content updates
"""

import sqlite3
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
import logging
import subprocess
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedAutoUpdatePipeline:
    def __init__(self, 
                 original_db="data/model_docs.db",
                 cleaned_db="data/model_docs_cleaned.db",
                 new_model_threshold=5,
                 updated_model_threshold=10,
                 field_change_threshold=20,
                 content_change_threshold=10000):  # characters
        """
        Initialize enhanced auto-update pipeline
        
        Args:
            original_db: Path to the original database
            cleaned_db: Path to the cleaned database  
            new_model_threshold: New models needed to trigger update
            updated_model_threshold: Updated models needed to trigger
            field_change_threshold: New/changed fields needed to trigger
            content_change_threshold: Character changes needed to trigger
        """
        self.original_db = Path(original_db)
        self.cleaned_db = Path(cleaned_db)
        self.new_model_threshold = new_model_threshold
        self.updated_model_threshold = updated_model_threshold
        self.field_change_threshold = field_change_threshold
        self.content_change_threshold = content_change_threshold
        self.state_file = Path("data/.enhanced_pipeline_state.json")
        
    def get_content_metrics(self, db_path) -> Dict:
        """Get detailed content metrics from database"""
        try:
            conn = sqlite3.connect(db_path)
            
            # Total models
            cursor = conn.execute("SELECT COUNT(*) FROM models")
            total_models = cursor.fetchone()[0]
            
            # Models with content
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT name) FROM models 
                WHERE section_data IS NOT NULL AND section_data != '{}'
            """)
            models_with_content = cursor.fetchone()[0]
            
            # Total content length
            cursor = conn.execute("""
                SELECT SUM(LENGTH(COALESCE(data, '')) + LENGTH(COALESCE(section_data, '')))
                FROM models
            """)
            total_content_length = cursor.fetchone()[0] or 0
            
            # Field counts by section
            field_counts = {}
            cursor = conn.execute("""
                SELECT name, section_data FROM models 
                WHERE section_data IS NOT NULL AND section_data != ''
            """)
            
            total_fields = 0
            for row in cursor:
                try:
                    section_data = json.loads(row[1])
                    for section, fields in section_data.items():
                        if isinstance(fields, dict):
                            non_empty = sum(1 for v in fields.values() if v and str(v).strip())
                            field_counts[section] = field_counts.get(section, 0) + non_empty
                            total_fields += non_empty
                except:
                    pass
            
            # Content hash for change detection
            cursor = conn.execute("""
                SELECT name, provider, data, section_data, updated_at
                FROM models ORDER BY name, provider
            """)
            
            content_parts = []
            for row in cursor:
                content_parts.append(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}")
            
            content_hash = hashlib.md5('\n'.join(content_parts).encode()).hexdigest()
            
            conn.close()
            
            return {
                "total_models": total_models,
                "models_with_content": models_with_content,
                "total_content_length": total_content_length,
                "total_fields": total_fields,
                "field_counts": field_counts,
                "content_hash": content_hash,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting content metrics: {e}")
            return {}
    
    def calculate_changes(self, current_metrics: Dict, previous_metrics: Dict) -> Tuple[Dict, bool]:
        """Calculate changes between current and previous metrics"""
        changes = {
            "new_models": current_metrics.get("total_models", 0) - previous_metrics.get("total_models", 0),
            "updated_content": current_metrics.get("content_hash") != previous_metrics.get("content_hash"),
            "content_length_change": current_metrics.get("total_content_length", 0) - previous_metrics.get("total_content_length", 0),
            "field_changes": current_metrics.get("total_fields", 0) - previous_metrics.get("total_fields", 0),
            "models_with_new_content": current_metrics.get("models_with_content", 0) - previous_metrics.get("models_with_content", 0)
        }
        
        # Check field-level changes
        current_fields = current_metrics.get("field_counts", {})
        previous_fields = previous_metrics.get("field_counts", {})
        
        field_increases = {}
        for section, count in current_fields.items():
            prev_count = previous_fields.get(section, 0)
            if count > prev_count:
                field_increases[section] = count - prev_count
        
        changes["field_increases"] = field_increases
        changes["total_field_increases"] = sum(field_increases.values())
        
        # Determine if update is needed
        needs_update = (
            changes["new_models"] >= self.new_model_threshold or
            changes["models_with_new_content"] >= self.updated_model_threshold or
            changes["total_field_increases"] >= self.field_change_threshold or
            changes["content_length_change"] >= self.content_change_threshold
        )
        
        return changes, needs_update
    
    def load_state(self):
        """Load pipeline state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {
            "last_update": None,
            "last_metrics": {},
            "total_updates": 0,
            "update_history": []
        }
    
    def save_state(self, state):
        """Save pipeline state"""
        self.state_file.parent.mkdir(exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def check_for_updates(self) -> Tuple[bool, Dict]:
        """Check if update is needed based on content changes"""
        state = self.load_state()
        
        # Get current metrics
        current_metrics = self.get_content_metrics(self.original_db)
        previous_metrics = state.get("last_metrics", {})
        
        # If no previous metrics, definitely update
        if not previous_metrics:
            logger.info("No previous metrics found, triggering initial update")
            return True, {"reason": "initial_run", "metrics": current_metrics}
        
        # Calculate changes
        changes, needs_update = self.calculate_changes(current_metrics, previous_metrics)
        
        # Log detailed changes
        logger.info(f"Content changes detected:")
        logger.info(f"  - New models: {changes['new_models']}")
        logger.info(f"  - Models with new content: {changes['models_with_new_content']}")
        logger.info(f"  - Total field increases: {changes['total_field_increases']}")
        logger.info(f"  - Content length change: {changes['content_length_change']:,} chars")
        
        if changes['field_increases']:
            logger.info(f"  - Fields added by section:")
            for section, count in changes['field_increases'].items():
                logger.info(f"    - {section}: +{count} fields")
        
        # Check if cleaned database exists
        if not self.cleaned_db.exists():
            logger.info("Cleaned database doesn't exist, triggering update")
            return True, {"reason": "missing_cleaned_db", "changes": changes}
        
        return needs_update, {"reason": "content_changes" if needs_update else "below_threshold", "changes": changes}
    
    def run_pipeline(self):
        """Run the complete cleaning and analysis pipeline"""
        logger.info("Starting enhanced data pipeline update...")
        
        start_time = time.time()
        
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
            
            # Update state with new metrics
            state = self.load_state()
            current_metrics = self.get_content_metrics(self.original_db)
            
            state["last_update"] = datetime.now().isoformat()
            state["last_metrics"] = current_metrics
            state["total_updates"] = state.get("total_updates", 0) + 1
            
            # Add to update history
            update_record = {
                "timestamp": datetime.now().isoformat(),
                "duration": time.time() - start_time,
                "metrics": current_metrics
            }
            
            history = state.get("update_history", [])
            history.append(update_record)
            # Keep last 10 updates
            state["update_history"] = history[-10:]
            
            self.save_state(state)
            
            logger.info(f"Pipeline update completed successfully in {time.time() - start_time:.2f}s!")
            return True
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return False
    
    def monitor_and_update(self, check_interval=300):
        """
        Monitor for changes and update when thresholds are met
        
        Args:
            check_interval: Seconds between checks (default: 5 minutes)
        """
        logger.info(f"Starting enhanced monitoring:")
        logger.info(f"  - Check interval: {check_interval}s")
        logger.info(f"  - New model threshold: {self.new_model_threshold}")
        logger.info(f"  - Updated model threshold: {self.updated_model_threshold}")
        logger.info(f"  - Field change threshold: {self.field_change_threshold}")
        logger.info(f"  - Content change threshold: {self.content_change_threshold:,} chars")
        
        while True:
            try:
                needs_update, info = self.check_for_updates()
                
                if needs_update:
                    logger.info(f"Update triggered! Reason: {info['reason']}")
                    success = self.run_pipeline()
                    
                    if success:
                        logger.info("Update completed successfully")
                    else:
                        logger.error("Update failed, will retry on next check")
                else:
                    logger.info(f"No update needed (reason: {info['reason']})")
                
                # Wait before next check
                logger.info(f"Next check in {check_interval}s...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(check_interval)
    
    def get_status(self):
        """Get current pipeline status"""
        state = self.load_state()
        current_metrics = self.get_content_metrics(self.original_db)
        previous_metrics = state.get("last_metrics", {})
        
        if previous_metrics:
            changes, needs_update = self.calculate_changes(current_metrics, previous_metrics)
        else:
            changes = None
            needs_update = True
        
        return {
            "last_update": state.get("last_update"),
            "total_updates": state.get("total_updates", 0),
            "current_metrics": current_metrics,
            "pending_changes": changes,
            "needs_update": needs_update,
            "update_history": state.get("update_history", [])
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced auto-update data pipeline")
    parser.add_argument("--new-models", type=int, default=5,
                      help="New models threshold (default: 5)")
    parser.add_argument("--updated-models", type=int, default=10,
                      help="Updated models threshold (default: 10)")
    parser.add_argument("--field-changes", type=int, default=20,
                      help="Field changes threshold (default: 20)")
    parser.add_argument("--content-changes", type=int, default=10000,
                      help="Content character changes threshold (default: 10000)")
    parser.add_argument("--interval", type=int, default=300,
                      help="Check interval in seconds (default: 300)")
    parser.add_argument("--once", action="store_true",
                      help="Run once instead of monitoring")
    parser.add_argument("--status", action="store_true",
                      help="Show current status and exit")
    
    args = parser.parse_args()
    
    pipeline = EnhancedAutoUpdatePipeline(
        new_model_threshold=args.new_models,
        updated_model_threshold=args.updated_models,
        field_change_threshold=args.field_changes,
        content_change_threshold=args.content_changes
    )
    
    if args.status:
        # Show status
        status = pipeline.get_status()
        print("\n=== Pipeline Status ===")
        print(f"Last update: {status['last_update'] or 'Never'}")
        print(f"Total updates: {status['total_updates']}")
        print(f"\nCurrent metrics:")
        metrics = status['current_metrics']
        print(f"  - Total models: {metrics.get('total_models', 0)}")
        print(f"  - Models with content: {metrics.get('models_with_content', 0)}")
        print(f"  - Total fields: {metrics.get('total_fields', 0)}")
        print(f"  - Content size: {metrics.get('total_content_length', 0):,} chars")
        
        if status['pending_changes']:
            print(f"\nPending changes:")
            changes = status['pending_changes']
            print(f"  - New models: {changes['new_models']}")
            print(f"  - Updated content: {'Yes' if changes['updated_content'] else 'No'}")
            print(f"  - Field changes: {changes['total_field_increases']}")
            print(f"  - Content change: {changes['content_length_change']:,} chars")
            print(f"\nUpdate needed: {'Yes' if status['needs_update'] else 'No'}")
    
    elif args.once:
        # Run once
        needs_update, info = pipeline.check_for_updates()
        if needs_update:
            logger.info(f"Running pipeline (reason: {info['reason']})")
            pipeline.run_pipeline()
        else:
            logger.info(f"No update needed ({info['reason']})")
    else:
        # Monitor continuously
        pipeline.monitor_and_update(check_interval=args.interval)


if __name__ == "__main__":
    main()