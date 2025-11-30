#!/bin/bash
# Setup cron job for automated pipeline

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_SCRIPT="$SCRIPT_DIR/automated_pipeline.sh"

# Create the cron job entry (runs daily at 2 AM)
CRON_JOB="0 2 * * * $PIPELINE_SCRIPT"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -F "$PIPELINE_SCRIPT" > /dev/null; then
    echo "Cron job already exists for the pipeline"
else
    # Add the cron job
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✓ Cron job added successfully!"
    echo "The pipeline will run daily at 2:00 AM"
fi

# Show current cron jobs
echo ""
echo "Current cron jobs:"
crontab -l | grep -F "$PIPELINE_SCRIPT" || echo "No pipeline cron jobs found"

echo ""
echo "To modify the schedule, edit your crontab with: crontab -e"
echo "To remove the cron job, run: crontab -l | grep -v '$PIPELINE_SCRIPT' | crontab -"