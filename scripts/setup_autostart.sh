#!/bin/bash
# =============================================================================
#            SMART C AI - SETUP AUTOSTART (Giải pháp đơn giản nhất)
# =============================================================================
# Script này cài đặt autostart bằng NHIỀU phương pháp đồng thời
# để đảm bảo app chạy được trên MỌI loại Pi desktop
#
# Chạy: bash scripts/setup_autostart.sh
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     🚀  SMART C AI - SETUP AUTOSTART                            ║"
echo "║         Giải pháp đơn giản và chắc chắn nhất                    ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "📁 App directory: $APP_HOME"
echo ""

# =====================================================
# 1. Tạo run script đơn giản
# =====================================================
echo -e "${GREEN}[1/4] Tạo run script...${NC}"

cat > "$APP_HOME/run.sh" << 'EOF'
#!/bin/bash
APP_HOME="$HOME/.digits"
[ ! -d "$APP_HOME" ] && APP_HOME="$HOME/.xiaozhi"

cd "$APP_HOME" || exit 1
mkdir -p logs

# Wait for desktop
sleep 5

# Setup display
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Auto-detect display
if [ -z "$WAYLAND_DISPLAY" ] && [ -z "$DISPLAY" ]; then
    # Try Wayland first
    for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
        if [ -e "$sock" ]; then
            export WAYLAND_DISPLAY=$(basename "$sock")
            export QT_QPA_PLATFORM=wayland
            break
        fi
    done
    # Fallback to X11
    if [ -z "$WAYLAND_DISPLAY" ]; then
        export DISPLAY=:0
        export QT_QPA_PLATFORM=xcb
    fi
else
    [ -n "$WAYLAND_DISPLAY" ] && export QT_QPA_PLATFORM=wayland
    [ -n "$DISPLAY" ] && export QT_QPA_PLATFORM=xcb
fi

# Start PulseAudio
pulseaudio --check 2>/dev/null || pulseaudio --start 2>/dev/null

# Kill old instance
pkill -f "python3 main.py" 2>/dev/null
sleep 1

# Log
echo "$(date): Starting Smart C AI (DISPLAY=$DISPLAY, WAYLAND=$WAYLAND_DISPLAY)" >> logs/smartc.log

# Run
exec python3 main.py --mode gui 2>&1 | tee -a logs/smartc.log
EOF

chmod +x "$APP_HOME/run.sh"
echo "   ✓ $APP_HOME/run.sh"

# =====================================================
# 2. Phương pháp 1: Cron @reboot (đơn giản nhất)
# =====================================================
echo -e "${GREEN}[2/4] Setup cron @reboot...${NC}"

# Remove old cron entries
crontab -l 2>/dev/null | grep -v "smartc\|run.sh\|digits" > /tmp/crontab.tmp || true

# Add new cron entry
echo "@reboot sleep 10 && $APP_HOME/run.sh >> $APP_HOME/logs/cron.log 2>&1" >> /tmp/crontab.tmp

crontab /tmp/crontab.tmp
rm /tmp/crontab.tmp

echo "   ✓ Cron @reboot đã cài đặt"

# =====================================================
# 3. Phương pháp 2: ~/.profile (chạy khi login)
# =====================================================
echo -e "${GREEN}[3/4] Setup ~/.profile autostart...${NC}"

# Remove old entries from .profile
if [ -f "$HOME/.profile" ]; then
    sed -i '/smartc\|run\.sh\|digits/d' "$HOME/.profile"
fi

# Add new entry
cat >> "$HOME/.profile" << EOF

# Smart C AI autostart
if [ -z "\$SMARTC_STARTED" ]; then
    export SMARTC_STARTED=1
    (sleep 15 && $APP_HOME/run.sh >> $APP_HOME/logs/profile.log 2>&1) &
fi
EOF

echo "   ✓ ~/.profile đã cập nhật"

# =====================================================
# 4. Phương pháp 3: Desktop autostart (backup)
# =====================================================
echo -e "${GREEN}[4/4] Setup desktop autostart...${NC}"

# labwc
mkdir -p "$HOME/.config/labwc"
cat > "$HOME/.config/labwc/autostart" << EOF
$APP_HOME/run.sh &
EOF
chmod +x "$HOME/.config/labwc/autostart"
echo "   ✓ ~/.config/labwc/autostart"

# Desktop entry
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/smartc.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Exec=$APP_HOME/run.sh
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
echo "   ✓ ~/.config/autostart/smartc.desktop"

# =====================================================
# Done
# =====================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ AUTOSTART ĐÃ CÀI ĐẶT!                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Đã cài đặt 3 phương pháp autostart:${NC}"
echo "  1. ⏰ Cron @reboot (sau 10 giây)"
echo "  2. 👤 ~/.profile (sau 15 giây khi login)"
echo "  3. 🖥️  Desktop autostart (labwc/LXDE)"
echo ""
echo -e "${YELLOW}Ít nhất 1 trong 3 phương pháp sẽ hoạt động!${NC}"
echo ""
echo -e "${CYAN}Test ngay:${NC}"
echo "   $APP_HOME/run.sh"
echo ""
echo -e "${CYAN}Hoặc reboot:${NC}"
echo "   sudo reboot"
echo ""
echo -e "${CYAN}Xem logs:${NC}"
echo "   tail -f $APP_HOME/logs/smartc.log"
echo "   tail -f $APP_HOME/logs/cron.log"
echo ""
