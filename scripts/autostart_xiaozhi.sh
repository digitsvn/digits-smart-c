#!/bin/bash
# Auto-start script for Xiaozhi AI on TV/Kiosk mode
# This script launches the app in fullscreen mode suitable for TV display

set -e

# Configuration
APP_PATH="/Users/nguyenduchoai/Desktop/Github/py-xiaozhi-pi/dist/xiaozhi.app"
LOG_DIR="/Users/nguyenduchoai/Desktop/Github/py-xiaozhi-pi/logs"
LOG_FILE="$LOG_DIR/autostart.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Log startup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Xiaozhi AI in TV mode..." >> "$LOG_FILE"

# Wait for network (important for OTA config)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Waiting for network..." >> "$LOG_FILE"
for i in {1..30}; do
    if ping -c 1 google.com &> /dev/null; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Network is ready" >> "$LOG_FILE"
        break
    fi
    sleep 1
done

# Kill any existing instance
pkill -f "xiaozhi.app" 2>/dev/null || true
sleep 1

# Launch the app
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Launching $APP_PATH" >> "$LOG_FILE"
open -a "$APP_PATH"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Xiaozhi AI started successfully" >> "$LOG_FILE"
