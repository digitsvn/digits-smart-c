#!/bin/bash
# =============================================================================
#            SMART C AI - CLEANUP OLD AUTOSTART
# =============================================================================
# Script này xóa tất cả các cách autostart cũ, chỉ giữ lại systemd service
# Chạy: bash scripts/cleanup_autostart.sh
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🧹 Cleaning up old autostart methods...${NC}"

APP_HOME="$HOME/.digits"
[ ! -d "$APP_HOME" ] && APP_HOME="$HOME/.xiaozhi"

# 1. Kill tất cả instances đang chạy
echo "Killing all running instances..."
pkill -9 -f "python3 main.py" 2>/dev/null || true
sleep 2

# 2. Xóa cron entries
echo "Removing cron entries..."
crontab -l 2>/dev/null | grep -v "smartc\|run.sh\|digits\|main.py" > /tmp/crontab.tmp || true
crontab /tmp/crontab.tmp 2>/dev/null || true
rm -f /tmp/crontab.tmp

# 3. Xóa ~/.profile autostart
echo "Removing ~/.profile autostart..."
if [ -f "$HOME/.profile" ]; then
    sed -i '/smartc\|run\.sh\|digits\|SMARTC_STARTED/d' "$HOME/.profile"
fi

# 4. Xóa labwc autostart
echo "Removing labwc autostart..."
rm -f "$HOME/.config/labwc/autostart"
mkdir -p "$HOME/.config/labwc"
touch "$HOME/.config/labwc/autostart"

# 5. Xóa desktop entry autostart
echo "Removing desktop entry autostart..."
rm -f "$HOME/.config/autostart/smartc.desktop"

# 6. Xóa lxsession autostart
echo "Removing lxsession autostart..."
if [ -f "$HOME/.config/lxsession/LXDE-pi/autostart" ]; then
    sed -i '/smartc\|run\.sh\|digits\|main.py/d' "$HOME/.config/lxsession/LXDE-pi/autostart"
fi

# 7. Kiểm tra còn process nào không
echo ""
echo "Checking for remaining processes..."
remaining=$(pgrep -f "python3 main.py" || true)
if [ -n "$remaining" ]; then
    echo -e "${YELLOW}⚠️  Còn processes đang chạy:${NC}"
    ps aux | grep "main.py" | grep -v grep
    echo ""
    echo "Force killing..."
    pkill -9 -f "python3 main.py" 2>/dev/null || true
else
    echo "✅ No remaining processes"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ CLEANUP HOÀN TẤT!                                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Bây giờ chỉ dùng systemd service để autostart."
echo ""
echo "Chạy: sudo systemctl restart smartc"
echo ""
