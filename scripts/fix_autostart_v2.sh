#!/bin/bash
# =============================================================================
#            SMART C AI - DEBUG & FIX AUTOSTART (V2)
# =============================================================================
# Script này debug và sửa triệt để lỗi autostart
# Chạy: bash scripts/fix_autostart_v2.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="$HOME/.digits"
if [ ! -d "$INSTALL_DIR" ]; then
    INSTALL_DIR="$HOME/.xiaozhi"
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     🔧  SMART C AI - DEBUG & FIX AUTOSTART V2                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =====================================================
# DEBUG: Kiểm tra môi trường
# =====================================================
echo -e "${YELLOW}=== DEBUG INFO ===${NC}"
echo "📁 Install dir: $INSTALL_DIR"
echo "👤 User: $USER"
echo "🏠 Home: $HOME"

# Kiểm tra Desktop Session
echo ""
echo -e "${YELLOW}Desktop Session:${NC}"
echo "  XDG_SESSION_TYPE: ${XDG_SESSION_TYPE:-not set}"
echo "  XDG_CURRENT_DESKTOP: ${XDG_CURRENT_DESKTOP:-not set}"
echo "  WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-not set}"
echo "  DISPLAY: ${DISPLAY:-not set}"

# Kiểm tra Display Manager
echo ""
echo -e "${YELLOW}Display Manager:${NC}"
if systemctl is-active lightdm 2>/dev/null | grep -q "active"; then
    echo "  ✓ LightDM đang chạy"
    DISPLAY_MANAGER="lightdm"
elif systemctl is-active gdm 2>/dev/null | grep -q "active"; then
    echo "  ✓ GDM đang chạy"
    DISPLAY_MANAGER="gdm"
else
    echo "  ⚠️  Không phát hiện Display Manager"
    DISPLAY_MANAGER="none"
fi

# Kiểm tra Window Manager
echo ""
echo -e "${YELLOW}Window Manager:${NC}"
if pgrep -x labwc > /dev/null 2>&1; then
    echo "  ✓ labwc đang chạy"
    WM="labwc"
elif pgrep -x openbox > /dev/null 2>&1; then
    echo "  ✓ Openbox đang chạy"
    WM="openbox"
elif pgrep -x wayfire > /dev/null 2>&1; then
    echo "  ✓ Wayfire đang chạy"
    WM="wayfire"
else
    echo "  ⚠️  Không phát hiện WM (có thể đang SSH)"
    WM="unknown"
fi

echo ""

# =====================================================
# FIX: Tạo run.sh mới với nhiều fallback
# =====================================================
echo -e "${GREEN}[1/4] Tạo run.sh với nhiều fallback...${NC}"

cat > "$INSTALL_DIR/run.sh" << 'RUNEOF'
#!/bin/bash
# Smart C AI Launcher (V2 - Enhanced)

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

cd "$APP_HOME" || exit 1
mkdir -p logs

LOG="$APP_HOME/logs/smartc.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG"
    echo "$1"
}

log "=========================================="
log "Smart C AI Starting..."
log "User: $USER"
log "Home: $HOME"
log "PWD: $(pwd)"

# Đợi desktop sẵn sàng
log "Waiting for desktop (5s)..."
sleep 5

# Thiết lập XDG_RUNTIME_DIR
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
log "XDG_RUNTIME_DIR: $XDG_RUNTIME_DIR"

# Phát hiện và thiết lập display
detect_display() {
    # Ưu tiên 1: Biến môi trường đã có
    if [ -n "$WAYLAND_DISPLAY" ]; then
        export QT_QPA_PLATFORM=wayland
        log "Using existing WAYLAND_DISPLAY: $WAYLAND_DISPLAY"
        return 0
    fi
    
    if [ -n "$DISPLAY" ]; then
        export QT_QPA_PLATFORM=xcb
        log "Using existing DISPLAY: $DISPLAY"
        return 0
    fi
    
    # Ưu tiên 2: Tìm Wayland socket
    local wayland_sock
    wayland_sock=$(ls "$XDG_RUNTIME_DIR"/wayland-* 2>/dev/null | head -1)
    if [ -n "$wayland_sock" ]; then
        export WAYLAND_DISPLAY=$(basename "$wayland_sock")
        export QT_QPA_PLATFORM=wayland
        log "Found Wayland socket: $WAYLAND_DISPLAY"
        return 0
    fi
    
    # Ưu tiên 3: Fallback X11
    export DISPLAY=:0
    export QT_QPA_PLATFORM=xcb
    log "Fallback to DISPLAY=:0"
    return 0
}

detect_display

# Khởi động PulseAudio nếu cần
if command -v pulseaudio &> /dev/null; then
    if ! pulseaudio --check 2>/dev/null; then
        log "Starting PulseAudio..."
        pulseaudio --start --daemonize=true 2>/dev/null || true
        sleep 1
    else
        log "PulseAudio already running"
    fi
fi

# Dừng instance cũ
pkill -f "python3 main.py" 2>/dev/null || true
pkill -f "python3 $APP_HOME/main.py" 2>/dev/null || true
sleep 1

# Ensure device ID
python3 "$APP_HOME/scripts/ensure_device_id_mac.py" 2>/dev/null || true

log "🚀 Launching Smart C AI..."
log "QT_QPA_PLATFORM: $QT_QPA_PLATFORM"

# Chạy app
exec python3 main.py --mode gui 2>&1 | tee -a "$LOG"
RUNEOF

chmod +x "$INSTALL_DIR/run.sh"
echo -e "${GREEN}✓ Đã tạo run.sh${NC}"

# =====================================================
# FIX: labwc autostart
# =====================================================
echo -e "${GREEN}[2/4] Cấu hình labwc autostart...${NC}"

mkdir -p "$HOME/.config/labwc"

# labwc autostart format: mỗi lệnh 1 dòng, không cần &
cat > "$HOME/.config/labwc/autostart" << EOF
# Smart C AI autostart for labwc
# Chạy sau 5 giây để đảm bảo desktop sẵn sàng
sleep 5 && $INSTALL_DIR/run.sh &
EOF

chmod +x "$HOME/.config/labwc/autostart"
echo -e "   📁 ~/.config/labwc/autostart"

# =====================================================
# FIX: wayfire autostart (nếu dùng wayfire)
# =====================================================
if [ -f "$HOME/.config/wayfire.ini" ]; then
    echo -e "${GREEN}[2b] Cấu hình wayfire autostart...${NC}"
    
    if ! grep -q "smartc" "$HOME/.config/wayfire.ini" 2>/dev/null; then
        cat >> "$HOME/.config/wayfire.ini" << EOF

[autostart]
smartc = $INSTALL_DIR/run.sh
EOF
        echo -e "   📁 ~/.config/wayfire.ini"
    fi
fi

# =====================================================
# FIX: Desktop Entry autostart
# =====================================================
echo -e "${GREEN}[3/4] Cấu hình Desktop Entry autostart...${NC}"

mkdir -p "$HOME/.config/autostart"

cat > "$HOME/.config/autostart/smartc.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Comment=Trợ lý AI thông minh
Exec=bash -c 'sleep 5 && $INSTALL_DIR/run.sh'
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
X-LXQt-Need-Tray=false
StartupNotify=false
Hidden=false
NoDisplay=false
EOF

echo -e "   📁 ~/.config/autostart/smartc.desktop"

# =====================================================
# FIX: LXSession autostart (Pi OS cũ)
# =====================================================
echo -e "${GREEN}[4/4] Cấu hình lxsession autostart...${NC}"

mkdir -p "$HOME/.config/lxsession/LXDE-pi"
LXSESSION_AUTOSTART="$HOME/.config/lxsession/LXDE-pi/autostart"

# Xóa entry cũ nếu có
if [ -f "$LXSESSION_AUTOSTART" ]; then
    sed -i '/smartc\|run\.sh/d' "$LXSESSION_AUTOSTART"
fi

# Thêm entry mới
echo "@bash -c 'sleep 5 && $INSTALL_DIR/run.sh'" >> "$LXSESSION_AUTOSTART"
echo -e "   📁 ~/.config/lxsession/LXDE-pi/autostart"

# =====================================================
# Thông tin hoàn tất
# =====================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ AUTOSTART ĐÃ ĐƯỢC SỬA!                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Các file đã cấu hình:${NC}"
echo "  📁 $INSTALL_DIR/run.sh"
echo "  📁 ~/.config/labwc/autostart"
echo "  📁 ~/.config/autostart/smartc.desktop"
echo "  📁 ~/.config/lxsession/LXDE-pi/autostart"
echo ""
echo -e "${YELLOW}⚡ Để test ngay (không cần reboot):${NC}"
echo "   $INSTALL_DIR/run.sh"
echo ""
echo -e "${YELLOW}🔄 Hoặc reboot để kiểm tra autostart:${NC}"
echo "   sudo reboot"
echo ""
echo -e "${CYAN}📝 Xem logs:${NC}"
echo "   tail -f $INSTALL_DIR/logs/smartc.log"
echo ""
