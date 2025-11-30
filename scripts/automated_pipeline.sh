#!/bin/bash
# Automated GPAI Model Documentation Pipeline
# Runs the complete pipeline: scraping → cleaning → analysis → scoring → export → sync

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Starting GPAI Model Documentation Pipeline ==="

# Change to project root
cd "$PROJECT_ROOT"

# 1. Run enhanced scraping
log "Step 1: Running enhanced scraping..."
if python scripts/enhanced_scraper.py >> "$LOG_FILE" 2>&1; then
    log "✓ Enhanced scraping completed"
else
    log "✗ Enhanced scraping failed"
fi

# 2. Run phase 2 scraping (HuggingFace, ArXiv, etc.)
log "Step 2: Running phase 2 scraping..."
if python scripts/run_phase2.py >> "$LOG_FILE" 2>&1; then
    log "✓ Phase 2 scraping completed"
else
    log "✗ Phase 2 scraping failed"
fi

# 3. Create cleaned database
log "Step 3: Creating cleaned database..."
if python scripts/create_cleaned_database.py >> "$LOG_FILE" 2>&1; then
    log "✓ Cleaned database created"
else
    log "✗ Cleaned database creation failed"
fi

# 4. Fix scoring consistency (using proper fix that checks both data and section_data)
log "Step 4: Fixing scoring consistency..."
if python scripts/fix_scoring_properly.py >> "$LOG_FILE" 2>&1; then
    log "✓ Scoring consistency fixed"
else
    log "✗ Scoring consistency fix failed"
fi

# 5. Run data analysis
log "Step 5: Running data analysis..."
if python scripts/data_analysis.py >> "$LOG_FILE" 2>&1; then
    log "✓ Data analysis completed"
else
    log "✗ Data analysis failed"
fi

# 6. Generate visualizations
log "Step 6: Generating visualizations..."
if python scripts/generate_visualizations.py >> "$LOG_FILE" 2>&1; then
    log "✓ Visualizations generated"
else
    log "✗ Visualization generation failed"
fi

# 7. Export to JSON
log "Step 7: Exporting data to JSON..."
if python scripts/db_export.py >> "$LOG_FILE" 2>&1; then
    log "✓ Data exported to JSON"
else
    log "✗ Data export failed"
fi

# 8. Sync to site
log "Step 8: Syncing data to site..."
if ./scripts/sync_data.sh >> "$LOG_FILE" 2>&1; then
    log "✓ Data synced to site"
else
    log "✗ Data sync failed"
fi

# 9. Generate dashboard data
log "Step 9: Generating dashboard data..."
if python scripts/generate_dashboard_data.py >> "$LOG_FILE" 2>&1; then
    log "✓ Dashboard data generated"
else
    log "✗ Dashboard data generation failed"
fi

log "=== Pipeline completed ==="

# Clean up old logs (keep only last 30 days)
find "$LOG_DIR" -name "pipeline_*.log" -mtime +30 -delete

exit 0