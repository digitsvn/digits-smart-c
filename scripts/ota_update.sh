#!/bin/bash
# =============================================================================
# Smart C AI - Staged OTA Update Script
# =============================================================================
# Safe update process with rollback capability:
# 1. Backup current version
# 2. Download and verify update
# 3. Apply update
# 4. Health check
# 5. Rollback if health check fails
# =============================================================================

set -e

# Configuration
APP_HOME="${HOME}/.digits"
BACKUP_DIR="/tmp/smartc-backup"
HEALTH_URL="http://localhost:8080/api/health"
HEALTH_TIMEOUT=60  # seconds to wait for health check
MAX_RETRIES=3

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if service is healthy
health_check() {
    local retries=0
    local wait_time=5
    
    log_info "Waiting for service to become healthy..."
    
    while [ $retries -lt $MAX_RETRIES ]; do
        sleep $wait_time
        
        response=$(curl -sf --max-time 10 "$HEALTH_URL" 2>/dev/null || true)
        
        if [ -n "$response" ]; then
            status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
            if [ "$status" = "healthy" ] || [ "$status" = "ok" ]; then
                log_info "Health check passed: $status"
                return 0
            elif [ "$status" = "degraded" ]; then
                log_warn "Service is degraded but functional"
                return 0
            fi
        fi
        
        retries=$((retries + 1))
        log_warn "Health check attempt $retries/$MAX_RETRIES failed"
        wait_time=$((wait_time * 2))  # Exponential backoff
    done
    
    log_error "Health check failed after $MAX_RETRIES attempts"
    return 1
}

# Backup current installation
backup_current() {
    log_info "Creating backup..."
    
    rm -rf "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    
    # Backup key files
    if [ -d "$APP_HOME" ]; then
        # Backup config (most important)
        if [ -f "$APP_HOME/config/config.json" ]; then
            cp "$APP_HOME/config/config.json" "$BACKUP_DIR/"
        fi
        
        # Backup VERSION for rollback verification
        if [ -f "$APP_HOME/VERSION" ]; then
            cp "$APP_HOME/VERSION" "$BACKUP_DIR/VERSION.old"
        fi
        
        # Create tarball of source (excluding logs, assets, venv)
        tar -czf "$BACKUP_DIR/source.tar.gz" \
            -C "$APP_HOME" \
            --exclude='logs' \
            --exclude='assets/videos' \
            --exclude='.venv' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            . 2>/dev/null || true
        
        log_info "Backup created at $BACKUP_DIR"
        return 0
    else
        log_error "App home not found: $APP_HOME"
        return 1
    fi
}

# Restore from backup
rollback() {
    log_warn "Rolling back to previous version..."
    
    if [ ! -d "$BACKUP_DIR" ] || [ ! -f "$BACKUP_DIR/source.tar.gz" ]; then
        log_error "No backup found to rollback to!"
        return 1
    fi
    
    # Stop service
    sudo systemctl stop smartc 2>/dev/null || true
    
    # Restore source
    cd "$APP_HOME"
    tar -xzf "$BACKUP_DIR/source.tar.gz" .
    
    # Restore config
    if [ -f "$BACKUP_DIR/config.json" ]; then
        cp "$BACKUP_DIR/config.json" "$APP_HOME/config/"
    fi
    
    # Restart service
    sudo systemctl start smartc
    
    sleep 5
    
    if health_check; then
        log_info "Rollback successful!"
        return 0
    else
        log_error "Rollback failed - manual intervention required"
        return 1
    fi
}

# Perform git update
do_update() {
    log_info "Fetching updates from remote..."
    
    cd "$APP_HOME"
    
    # Fetch changes
    git fetch origin main 2>&1
    
    # Check if there are updates
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)
    
    if [ "$LOCAL" = "$REMOTE" ]; then
        log_info "Already up to date!"
        return 0
    fi
    
    log_info "Updates available: $LOCAL -> $REMOTE"
    
    # Get commit messages for changelog
    log_info "Changes:"
    git log --oneline "$LOCAL..$REMOTE" | head -10
    
    # Apply update
    log_info "Applying update..."
    git reset --hard origin/main
    
    # Update dependencies if requirements changed
    if git diff --name-only "$LOCAL..$REMOTE" | grep -q "requirements.txt"; then
        log_info "Updating Python dependencies..."
        pip install -r requirements.txt --quiet
    fi
    
    return 0
}

# Main update flow
main() {
    echo "=============================================="
    echo "  Smart C AI - Staged OTA Update"
    echo "=============================================="
    echo ""
    
    # Step 1: Backup
    log_info "Step 1/5: Creating backup..."
    if ! backup_current; then
        log_error "Backup failed, aborting update"
        exit 1
    fi
    
    # Step 2: Stop service
    log_info "Step 2/5: Stopping service..."
    sudo systemctl stop smartc 2>/dev/null || true
    sleep 2
    
    # Step 3: Apply update
    log_info "Step 3/5: Applying update..."
    if ! do_update; then
        log_error "Update failed, attempting rollback..."
        rollback
        exit 1
    fi
    
    # Restore config (in case update overwrote it)
    if [ -f "$BACKUP_DIR/config.json" ]; then
        cp "$BACKUP_DIR/config.json" "$APP_HOME/config/"
        log_info "Config preserved"
    fi
    
    # Step 4: Restart service
    log_info "Step 4/5: Starting service..."
    sudo systemctl start smartc
    
    # Step 5: Health check
    log_info "Step 5/5: Verifying health..."
    if health_check; then
        echo ""
        log_info "=============================================="
        log_info "  UPDATE SUCCESSFUL!"
        log_info "=============================================="
        
        # Show new version
        if [ -f "$APP_HOME/VERSION" ]; then
            NEW_VERSION=$(cat "$APP_HOME/VERSION")
            log_info "New version: $NEW_VERSION"
        fi
        
        # Cleanup backup after successful update
        rm -rf "$BACKUP_DIR"
        
        exit 0
    else
        log_error "Health check failed after update"
        log_warn "Initiating automatic rollback..."
        
        if rollback; then
            log_warn "Rollback completed. Please check logs for details."
        fi
        
        exit 1
    fi
}

# Handle arguments
case "${1:-}" in
    --rollback)
        rollback
        ;;
    --health)
        health_check
        ;;
    --backup)
        backup_current
        ;;
    *)
        main
        ;;
esac
