#!/bin/bash
# =============================================================================
# Smart C AI Watchdog Service
# =============================================================================
# Monitors the Smart C AI application and automatically restarts it if:
# - The process crashes
# - The health endpoint is unresponsive
# - Memory usage exceeds threshold
#
# Install: sudo cp scripts/watchdog.sh /usr/local/bin/smartc-watchdog
#          sudo chmod +x /usr/local/bin/smartc-watchdog
#          sudo cp scripts/smartc-watchdog.service /etc/systemd/system/
#          sudo systemctl enable smartc-watchdog
#          sudo systemctl start smartc-watchdog
# =============================================================================

# Configuration
APP_NAME="smartc"
HEALTH_URL="http://localhost:8080/api/health"
CHECK_INTERVAL=30  # seconds
MAX_MEMORY_PERCENT=85
MAX_CONSECUTIVE_FAILURES=3
LOG_FILE="$HOME/.digits/logs/watchdog.log"

# Counters
consecutive_failures=0

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_process() {
    # Check if smartc service is running
    if systemctl is-active --quiet "$APP_NAME" 2>/dev/null; then
        return 0
    fi
    return 1
}

check_health() {
    # Check health endpoint with timeout
    response=$(curl -sf --max-time 10 "$HEALTH_URL" 2>/dev/null)
    if [ $? -eq 0 ]; then
        # Parse status from JSON response
        status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$status" = "healthy" ] || [ "$status" = "ok" ]; then
            return 0
        fi
    fi
    return 1
}

check_memory() {
    # Get memory usage percentage for the smartc process
    pid=$(pgrep -f "python.*main.py" | head -1)
    if [ -n "$pid" ]; then
        mem_percent=$(ps -o %mem= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$mem_percent" ]; then
            # Compare as integers (bash doesn't do float comparison well)
            mem_int=${mem_percent%.*}
            if [ "$mem_int" -gt "$MAX_MEMORY_PERCENT" ]; then
                log "WARNING: Memory usage ${mem_percent}% exceeds threshold ${MAX_MEMORY_PERCENT}%"
                return 1
            fi
        fi
    fi
    return 0
}

restart_service() {
    log "RESTARTING: $APP_NAME service..."
    systemctl restart "$APP_NAME"
    sleep 10  # Wait for startup
    
    if check_process; then
        log "SUCCESS: Service restarted successfully"
        consecutive_failures=0
        return 0
    else
        log "ERROR: Service failed to restart"
        return 1
    fi
}

# Main watchdog loop
log "=========================================="
log "Smart C AI Watchdog Started"
log "Health URL: $HEALTH_URL"
log "Check Interval: ${CHECK_INTERVAL}s"
log "Max Memory: ${MAX_MEMORY_PERCENT}%"
log "=========================================="

while true; do
    needs_restart=false
    reason=""
    
    # Check 1: Process running?
    if ! check_process; then
        needs_restart=true
        reason="Process not running"
    fi
    
    # Check 2: Health endpoint responding?
    if [ "$needs_restart" = false ]; then
        if ! check_health; then
            consecutive_failures=$((consecutive_failures + 1))
            log "WARNING: Health check failed ($consecutive_failures/$MAX_CONSECUTIVE_FAILURES)"
            
            if [ "$consecutive_failures" -ge "$MAX_CONSECUTIVE_FAILURES" ]; then
                needs_restart=true
                reason="Health endpoint unresponsive"
            fi
        else
            consecutive_failures=0
        fi
    fi
    
    # Check 3: Memory usage (optional restart)
    if [ "$needs_restart" = false ]; then
        if ! check_memory; then
            # Only restart if memory is critically high (over 95%)
            pid=$(pgrep -f "python.*main.py" | head -1)
            if [ -n "$pid" ]; then
                mem_percent=$(ps -o %mem= -p "$pid" 2>/dev/null | tr -d ' ')
                mem_int=${mem_percent%.*}
                if [ "$mem_int" -gt 95 ]; then
                    needs_restart=true
                    reason="Critical memory usage (${mem_percent}%)"
                fi
            fi
        fi
    fi
    
    # Perform restart if needed
    if [ "$needs_restart" = true ]; then
        log "ALERT: Restart required - $reason"
        restart_service
    fi
    
    sleep "$CHECK_INTERVAL"
done
