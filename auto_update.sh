#!/bin/bash
# =============================================================================
#            SMART C AI - AUTO UPDATE ON BOOT
# =============================================================================
# Script này tự động kiểm tra và cập nhật Smart C AI mỗi khi khởi động
# 
# Cài đặt: bash auto_update.sh --install
# Gỡ bỏ:   bash auto_update.sh --uninstall
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

SYSTEMD_SERVICE="/etc/systemd/system/smartc-update.service"
SYSTEMD_TIMER="/etc/systemd/system/smartc-update.timer"
UPDATE_SCRIPT="$APP_HOME/scripts/boot_update.sh"

# =====================================================
# Tạo boot update script
# =====================================================
create_boot_update_script() {
    mkdir -p "$APP_HOME/scripts"
    
    cat > "$UPDATE_SCRIPT" << 'BOOTSCRIPT'
#!/bin/bash
# Smart C AI - Boot Update Script
# Chạy mỗi khi khởi động để kiểm tra và cập nhật

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

LOG_FILE="$APP_HOME/logs/update.log"
mkdir -p "$APP_HOME/logs"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "=== Bắt đầu kiểm tra cập nhật ==="

cd "$APP_HOME" || exit 1

# Kiểm tra có phải git repo không
if [ ! -d ".git" ]; then
    log "Không phải git repo, bỏ qua"
    exit 0
fi

# Kiểm tra kết nối mạng
if ! ping -c 1 github.com &> /dev/null; then
    log "Không có kết nối mạng, bỏ qua"
    exit 0
fi

# Fetch từ remote
git fetch origin main 2>> "$LOG_FILE"

# So sánh local vs remote
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "Đã là phiên bản mới nhất: $LOCAL"
    exit 0
fi

log "Phát hiện phiên bản mới: $REMOTE (hiện tại: $LOCAL)"

# Backup config
BACKUP_DIR="/tmp/smartc_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "$APP_HOME/config/config.json" ]; then
    cp "$APP_HOME/config/config.json" "$BACKUP_DIR/"
    log "Backup: config.json"
fi

if [ -f "$APP_HOME/config/efuse.json" ]; then
    cp "$APP_HOME/config/efuse.json" "$BACKUP_DIR/"
    log "Backup: efuse.json"
fi

if [ -f "$APP_HOME/config/.first_run_done" ]; then
    cp "$APP_HOME/config/.first_run_done" "$BACKUP_DIR/"
fi

# Pull code mới
git stash 2>> "$LOG_FILE" || true
git reset --hard origin/main 2>> "$LOG_FILE"
log "Đã pull code mới"

# Khôi phục config
if [ -f "$BACKUP_DIR/config.json" ]; then
    cp "$BACKUP_DIR/config.json" "$APP_HOME/config/"
fi
if [ -f "$BACKUP_DIR/efuse.json" ]; then
    cp "$BACKUP_DIR/efuse.json" "$APP_HOME/config/"
fi
if [ -f "$BACKUP_DIR/.first_run_done" ]; then
    cp "$BACKUP_DIR/.first_run_done" "$APP_HOME/config/"
fi
log "Đã khôi phục config"

# Cấp quyền thực thi
chmod +x "$APP_HOME/run.sh" 2>/dev/null || true
chmod +x "$APP_HOME/run_cli.sh" 2>/dev/null || true
chmod +x "$APP_HOME/update.sh" 2>/dev/null || true
chmod +x "$APP_HOME/scripts/"*.sh 2>/dev/null || true

log "=== Cập nhật hoàn tất: $REMOTE ==="
BOOTSCRIPT

    chmod +x "$UPDATE_SCRIPT"
    echo -e "${GREEN}✓ Tạo boot update script${NC}"
}

# =====================================================
# Cài đặt systemd service (chạy 1 lần khi boot)
# =====================================================
install_systemd() {
    # Service file
    sudo tee "$SYSTEMD_SERVICE" > /dev/null << EOF
[Unit]
Description=Smart C AI Auto Update
After=network-online.target
Wants=network-online.target
Before=smartc.service

[Service]
Type=oneshot
User=$USER
ExecStart=$UPDATE_SCRIPT
StandardOutput=append:$APP_HOME/logs/update.log
StandardError=append:$APP_HOME/logs/update.log
TimeoutStartSec=120

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable smartc-update.service
    
    echo -e "${GREEN}✓ Cài đặt systemd service${NC}"
}

# =====================================================
# Gỡ cài đặt
# =====================================================
uninstall() {
    echo -e "${YELLOW}Gỡ cài đặt auto-update...${NC}"
    
    sudo systemctl disable smartc-update.service 2>/dev/null || true
    sudo rm -f "$SYSTEMD_SERVICE" 2>/dev/null || true
    sudo rm -f "$SYSTEMD_TIMER" 2>/dev/null || true
    sudo systemctl daemon-reload
    
    rm -f "$UPDATE_SCRIPT" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Đã gỡ cài đặt auto-update${NC}"
}

# =====================================================
# Main
# =====================================================
case "$1" in
    --install|-i)
        echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${CYAN}║     🔄  SMART C AI - AUTO UPDATE ON BOOT                        ║${NC}"
        echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
        echo
        
        create_boot_update_script
        install_systemd
        
        echo
        echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║          ✅ AUTO-UPDATE ĐÃ CÀI ĐẶT!                    ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
        echo
        echo "Mỗi khi khởi động, hệ thống sẽ:"
        echo "  1. Kiểm tra phiên bản mới từ GitHub"
        echo "  2. Nếu có → Tự động cập nhật + giữ config"
        echo "  3. Khởi động Smart C AI"
        echo
        echo -e "📁 Log: $APP_HOME/logs/update.log"
        echo -e "🔧 Gỡ bỏ: ${YELLOW}bash auto_update.sh --uninstall${NC}"
        ;;
        
    --uninstall|-u)
        uninstall
        ;;
        
    *)
        echo "Smart C AI - Auto Update on Boot"
        echo
        echo "Cách dùng:"
        echo "  bash auto_update.sh --install     # Cài đặt auto-update"
        echo "  bash auto_update.sh --uninstall   # Gỡ bỏ auto-update"
        echo
        echo "Khi cài đặt, mỗi lần boot Pi sẽ tự động:"
        echo "  - Kiểm tra phiên bản mới từ GitHub"
        echo "  - Cập nhật nếu có phiên bản mới"
        echo "  - Giữ nguyên config (config.json, efuse.json)"
        ;;
esac
