#!/bin/bash
# =============================================================================
#            SMART C AI - FIX AUTOSTART
# =============================================================================
# Script này sửa lỗi autostart trên Pi đã cài đặt
# Chạy: bash scripts/fix_autostart.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/.digits"
if [ ! -d "$INSTALL_DIR" ]; then
    INSTALL_DIR="$HOME/.xiaozhi"
fi

if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}❌ Không tìm thấy thư mục cài đặt Smart C AI${NC}"
    echo "Vui lòng chạy installer trước:"
    echo "  git clone https://github.com/nguyenduchoai/py-xiaozhi-pi.git ~/.digits"
    echo "  cd ~/.digits && bash install_oslite.sh"
    exit 1
fi

echo -e "${GREEN}🔧 Đang sửa autostart cho Smart C AI...${NC}"
echo "   📁 Thư mục: $INSTALL_DIR"

# =========================================
# 1. Cập nhật run.sh với delay
# =========================================
cat > "$INSTALL_DIR/run.sh" << 'RUNEOF'
#!/bin/bash
# Smart C AI Launcher (Fixed)

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

# Đợi desktop sẵn sàng (quan trọng cho autostart)
sleep 3

cd "$APP_HOME"
mkdir -p logs

# Log khởi động
echo "$(date): Smart C AI starting..." >> logs/smartc.log

# Detect display environment
if [ -n "$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM=wayland
    echo "$(date): Running on Wayland: $WAYLAND_DISPLAY" >> logs/smartc.log
elif [ -n "$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
    echo "$(date): Running on X11: $DISPLAY" >> logs/smartc.log
else
    # Try to find Wayland socket
    WAYLAND_SOCK=$(ls /run/user/$(id -u)/wayland-* 2>/dev/null | head -1)
    if [ -n "$WAYLAND_SOCK" ]; then
        export WAYLAND_DISPLAY=$(basename "$WAYLAND_SOCK")
        export QT_QPA_PLATFORM=wayland
        echo "$(date): Found Wayland socket: $WAYLAND_DISPLAY" >> logs/smartc.log
    else
        export DISPLAY=:0
        export QT_QPA_PLATFORM=xcb
        echo "$(date): Fallback to DISPLAY=:0" >> logs/smartc.log
    fi
fi

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

# Start PulseAudio if not running
if ! pulseaudio --check 2>/dev/null; then
    pulseaudio --start --daemonize=true 2>/dev/null || true
    sleep 1
fi

# Ensure device ID
python3 "$APP_HOME/scripts/ensure_device_id_mac.py" 2>/dev/null || true

# Stop existing instance
pkill -f "python3 main.py" 2>/dev/null
sleep 0.5

echo "$(date): 🚀 Starting Smart C AI..." >> logs/smartc.log
exec python3 main.py --mode gui 2>&1 | tee -a logs/smartc.log
RUNEOF

chmod +x "$INSTALL_DIR/run.sh"
echo -e "${GREEN}✓ Cập nhật run.sh với delay khởi động${NC}"

# =========================================
# 2. Autostart cho labwc (Raspberry Pi Wayland)
# =========================================
mkdir -p "$HOME/.config/labwc"
cat > "$HOME/.config/labwc/autostart" << EOF
# Smart C AI - Auto start
$INSTALL_DIR/run.sh &
EOF
chmod +x "$HOME/.config/labwc/autostart"
echo -e "${GREEN}✓ Cấu hình labwc autostart${NC}"

# =========================================
# 3. Autostart cho LXDE/LXQt/GNOME
# =========================================
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/smartc.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Comment=Trợ lý AI thông minh
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
X-GNOME-Autostart-enabled=true
X-LXDE-Autostart-enabled=true
StartupNotify=false
EOF
echo -e "${GREEN}✓ Cấu hình desktop autostart${NC}"

# =========================================
# 4. Autostart cho lxsession (Pi Desktop cũ)
# =========================================
mkdir -p "$HOME/.config/lxsession/LXDE-pi"
LXSESSION_AUTOSTART="$HOME/.config/lxsession/LXDE-pi/autostart"
if [ ! -f "$LXSESSION_AUTOSTART" ]; then
    touch "$LXSESSION_AUTOSTART"
fi
if ! grep -q "smartc\|run.sh" "$LXSESSION_AUTOSTART" 2>/dev/null; then
    echo "@$INSTALL_DIR/run.sh" >> "$LXSESSION_AUTOSTART"
    echo -e "${GREEN}✓ Cấu hình lxsession autostart${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✅ AUTOSTART ĐÃ ĐƯỢC SỬA!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "📍 Các file đã cấu hình:"
echo "   - ~/.config/labwc/autostart (labwc/Wayland)"
echo "   - ~/.config/autostart/smartc.desktop (GNOME/LXDE)"
echo "   - ~/.config/lxsession/LXDE-pi/autostart (lxsession)"
echo ""
echo "🔄 Vui lòng reboot để kiểm tra:"
echo "   sudo reboot"
echo ""
