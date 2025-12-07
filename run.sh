#!/bin/bash
#
# Watts-A Supervisor Script
# Auto-restarts main.py on crash for 24/7 operation
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Watts-A Broadcast Station Supervisor"
echo "============================================"
echo "Working directory: $SCRIPT_DIR"
echo "Crash log: $SCRIPT_DIR/crash.log"
echo ""
echo "Press Ctrl+C to stop"
echo "============================================"

while true; do
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Watts-A Broadcast Station..."

    # Run the main Python script
    python3 main.py

    # Capture exit code
    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        # Crash detected
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] CRASH detected! Exit code: $EXIT_CODE"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Exit code: $EXIT_CODE" >> crash.log

        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restarting in 5 seconds..."
        sleep 5
    else
        # Clean exit (e.g., user pressed Ctrl+C)
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Clean exit detected."
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restarting in 2 seconds..."
        sleep 2
    fi
done
