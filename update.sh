#!/bin/bash
# =============================================================================
#            SMART C AI - UPDATE SCRIPT
# =============================================================================
# Script này cập nhật Smart C AI trên Pi đang chạy
# Chạy: bash update.sh
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

if [ ! -d "$APP_HOME" ]; then
    echo -e "${RED}❌ Không tìm thấy thư mục Smart C AI${NC}"
    echo "Vui lòng cài đặt trước: bash install_oslite.sh"
    exit 1
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║     🔄  SMART C AI - UPDATE                                     ║"
echo "║         Cập nhật ứng dụng lên phiên bản mới nhất               ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}📁 Thư mục: $APP_HOME${NC}"
echo

# =====================================================
# 1. Dừng app đang chạy
# =====================================================
echo -e "${YELLOW}[1/5] Dừng app đang chạy...${NC}"
pkill -f "python3 main.py" 2>/dev/null || true
pkill -f "python3 $APP_HOME/main.py" 2>/dev/null || true
sudo systemctl stop smartc 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓ App đã dừng${NC}"

# =====================================================
# 2. Backup config
# =====================================================
echo -e "${YELLOW}[2/5] Backup config...${NC}"
BACKUP_DIR="/tmp/smartc_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -f "$APP_HOME/config/config.json" ]; then
    cp "$APP_HOME/config/config.json" "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backup: config.json${NC}"
fi

if [ -f "$APP_HOME/config/efuse.json" ]; then
    cp "$APP_HOME/config/efuse.json" "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backup: efuse.json${NC}"
fi

if [ -f "$APP_HOME/config/.first_run_done" ]; then
    cp "$APP_HOME/config/.first_run_done" "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backup: .first_run_done${NC}"
fi

echo -e "${GREEN}✓ Backup tại: $BACKUP_DIR${NC}"

# =====================================================
# 3. Pull code mới
# =====================================================
echo -e "${YELLOW}[3/5] Pull code mới từ GitHub...${NC}"
cd "$APP_HOME"

# Kiểm tra xem có phải git repo không
if [ -d ".git" ]; then
    # Stash local changes (nếu có)
    git stash 2>/dev/null || true
    
    # Pull code mới
    git fetch origin main
    git reset --hard origin/main
    
    echo -e "${GREEN}✓ Đã pull code mới${NC}"
else
    echo -e "${YELLOW}⚠️  Không phải git repo, skip pull${NC}"
fi

# =====================================================
# 4. Khôi phục config
# =====================================================
echo -e "${YELLOW}[4/5] Khôi phục config...${NC}"

if [ -f "$BACKUP_DIR/config.json" ]; then
    cp "$BACKUP_DIR/config.json" "$APP_HOME/config/"
    echo -e "${GREEN}✓ Khôi phục: config.json${NC}"
fi

if [ -f "$BACKUP_DIR/efuse.json" ]; then
    cp "$BACKUP_DIR/efuse.json" "$APP_HOME/config/"
    echo -e "${GREEN}✓ Khôi phục: efuse.json${NC}"
fi

if [ -f "$BACKUP_DIR/.first_run_done" ]; then
    cp "$BACKUP_DIR/.first_run_done" "$APP_HOME/config/"
    echo -e "${GREEN}✓ Khôi phục: .first_run_done${NC}"
fi

# Đảm bảo scripts có quyền thực thi
chmod +x "$APP_HOME/run.sh" 2>/dev/null || true
chmod +x "$APP_HOME/run_cli.sh" 2>/dev/null || true
chmod +x "$APP_HOME/scripts/"*.sh 2>/dev/null || true

echo -e "${GREEN}✓ Config đã khôi phục${NC}"

# =====================================================
# 5. Khởi động lại app
# =====================================================
echo -e "${YELLOW}[5/5] Khởi động lại app...${NC}"

# Kiểm tra mode (systemd hoặc GUI)
if systemctl is-enabled smartc 2>/dev/null | grep -q "enabled"; then
    echo "Sử dụng systemd service..."
    sudo systemctl start smartc
    sleep 2
    if systemctl is-active smartc 2>/dev/null | grep -q "active"; then
        echo -e "${GREEN}✓ Service smartc đã khởi động${NC}"
    else
        echo -e "${YELLOW}⚠️  Service chưa active, kiểm tra logs${NC}"
    fi
else
    # Khởi động bằng run.sh (GUI mode)
    if [ -f "$APP_HOME/run.sh" ]; then
        echo "Sử dụng run.sh..."
        nohup "$APP_HOME/run.sh" > /dev/null 2>&1 &
        sleep 3
        if pgrep -f "python3 main.py" > /dev/null; then
            echo -e "${GREEN}✓ App đã khởi động (GUI mode)${NC}"
        else
            echo -e "${YELLOW}⚠️  App chưa khởi động, kiểm tra logs${NC}"
        fi
    fi
fi

# =====================================================
# Hoàn tất
# =====================================================
echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✅ UPDATE HOÀN TẤT!                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "📍 Phiên bản mới đã được cập nhật"
echo -e "📍 Config đã được giữ nguyên"
echo -e "📍 Backup: $BACKUP_DIR"
echo
echo -e "${CYAN}Xem logs:${NC}"
echo "   tail -f $APP_HOME/logs/smartc.log"
echo
echo -e "${CYAN}Kiểm tra trạng thái:${NC}"
echo "   sudo systemctl status smartc"
echo
