#!/bin/bash
# =============================================================================
#            SMART C AI - QUICK UPDATE (Giữ config)
# =============================================================================
# Script này update code MÀ KHÔNG MẤT CONFIG
# Chạy: bash quick_update.sh
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
    exit 1
fi

cd "$APP_HOME"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     🔄  SMART C AI - QUICK UPDATE (Giữ config)                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Backup config
echo -e "${YELLOW}[1/4] Backup config...${NC}"
BACKUP_DIR="/tmp/smartc_config_backup"
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

if [ -f "config/config.json" ]; then
    cp config/config.json "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backup: config.json${NC}"
fi
if [ -f "config/efuse.json" ]; then
    cp config/efuse.json "$BACKUP_DIR/"
    echo -e "${GREEN}✓ Backup: efuse.json${NC}"
fi
if [ -f "config/.first_run_done" ]; then
    cp config/.first_run_done "$BACKUP_DIR/"
fi

# 2. Pull code
echo -e "${YELLOW}[2/4] Pull code mới...${NC}"
git fetch origin main
git reset --hard origin/main
echo -e "${GREEN}✓ Code đã update${NC}"

# 3. Restore config
echo -e "${YELLOW}[3/4] Khôi phục config...${NC}"
mkdir -p config
if [ -f "$BACKUP_DIR/config.json" ]; then
    cp "$BACKUP_DIR/config.json" config/
    echo -e "${GREEN}✓ Khôi phục: config.json${NC}"
fi
if [ -f "$BACKUP_DIR/efuse.json" ]; then
    cp "$BACKUP_DIR/efuse.json" config/
    echo -e "${GREEN}✓ Khôi phục: efuse.json${NC}"
fi
if [ -f "$BACKUP_DIR/.first_run_done" ]; then
    cp "$BACKUP_DIR/.first_run_done" config/
fi

# 4. Restart app
echo -e "${YELLOW}[4/4] Khởi động lại...${NC}"
pkill -9 -f "python3 main.py" 2>/dev/null || true
sleep 1

export DISPLAY=:0
nohup python3 main.py --mode gui > /dev/null 2>&1 &
sleep 2

echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✅ UPDATE HOÀN TẤT - CONFIG ĐÃ GIỮ!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "📋 Config: $(cat config/config.json | grep -o '\"i2s_enabled\": [^,]*' | head -1)"
echo -e "📋 HDMI: $(cat config/config.json | grep -o '\"hdmi_audio\": [^,]*' | head -1)"
echo
