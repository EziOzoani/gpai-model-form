#!/bin/bash
# Script to run the complete analytics pipeline and start servers

echo "=== GPAI Model Analytics Pipeline ==="

# Change to script directory
cd "$(dirname "$0")"

# Step 1: Run the data pipeline
echo "Running data pipeline..."
python scripts/auto_update_pipeline.py --once

# Check if successful
if [ $? -ne 0 ]; then
    echo "Error: Data pipeline failed"
    exit 1
fi

echo "Data pipeline completed successfully!"

# Step 2: Start API server in background
echo "Starting API server on port 5001..."
python api/analysis_endpoints.py &
API_PID=$!

echo "API server started with PID: $API_PID"

# Step 3: Start React development server
echo "Starting React development server..."
cd site
npm run dev &
REACT_PID=$!

echo "React server started with PID: $REACT_PID"

# Function to cleanup on exit
cleanup() {
    echo "Shutting down servers..."
    kill $API_PID 2>/dev/null
    kill $REACT_PID 2>/dev/null
    exit 0
}

# Set up cleanup on script exit
trap cleanup INT TERM

# Wait for user to stop
echo ""
echo "Analytics system is running!"
echo "- API: http://localhost:5001"
echo "- Dashboard: http://localhost:5173/analytics"
echo ""
echo "Press Ctrl+C to stop all services"

# Keep script running
wait