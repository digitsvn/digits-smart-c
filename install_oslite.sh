#!/bin/bash
# =============================================================================
#            SMART C AI - RASPBERRY PI OS LITE INSTALLER
# =============================================================================
# Script này cài đặt Smart C AI trên Raspberry Pi OS Lite
# 
# Yêu cầu:
# - Raspberry Pi OS Lite (64-bit recommended)
# - Kết nối Internet (Ethernet hoặc WiFi đã cấu hình)
#
# Chạy: bash install_oslite.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_NAME="smartc"
INSTALL_DIR="$HOME/.digits"
LOG_FILE="/tmp/smartc_install.log"

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ❌ $1${NC}" | tee -a "$LOG_FILE"
}

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║     🤖  SMART C AI - Raspberry Pi OS Lite Installer             ║"
    echo "║                                                                  ║"
    echo "║     Website: https://xiaozhi-ai-iot.vn                           ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "Không chạy script này với sudo/root!"
        log "Chạy lại: bash install_oslite.sh"
        exit 1
    fi
}

check_raspberry_pi() {
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        log "Phát hiện: $MODEL"
    else
        log_warn "Không phát hiện Raspberry Pi, tiếp tục..."
    fi
}

# =============================================================================
# BƯỚC 0: Cấu hình HDMI Display (Full HD 1920x1080)
# =============================================================================
configure_display() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 0: Cấu hình Display (Full HD 1920x1080)"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Xác định file config.txt (Pi OS cũ vs mới)
    if [ -f /boot/firmware/config.txt ]; then
        CONFIG_FILE="/boot/firmware/config.txt"
    elif [ -f /boot/config.txt ]; then
        CONFIG_FILE="/boot/config.txt"
    else
        log_warn "Không tìm thấy config.txt, bỏ qua cấu hình display"
        return 0
    fi
    
    log "Sử dụng config file: $CONFIG_FILE"
    
    # Backup config file
    sudo cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Xóa các cấu hình HDMI cũ (nếu có)
    sudo sed -i '/^hdmi_group=/d' "$CONFIG_FILE"
    sudo sed -i '/^hdmi_mode=/d' "$CONFIG_FILE"
    sudo sed -i '/^hdmi_force_hotplug=/d' "$CONFIG_FILE"
    sudo sed -i '/^disable_overscan=/d' "$CONFIG_FILE"
    sudo sed -i '/^hdmi_drive=/d' "$CONFIG_FILE"
    
    # Thêm cấu hình HDMI Full HD 1920x1080 60Hz
    log "Cấu hình HDMI: 1920x1080 @ 60Hz"
    
    cat << 'HDMI_CONFIG' | sudo tee -a "$CONFIG_FILE" > /dev/null

# ============================================
# Smart C AI - HDMI Configuration (Full HD)
# ============================================
# hdmi_group=2 = DMT (monitor mode)
# hdmi_mode=82 = 1920x1080 @ 60Hz
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
hdmi_drive=2
disable_overscan=1
HDMI_CONFIG
    
    log "✓ HDMI đã cấu hình: 1920x1080 @ 60Hz"
}

# =============================================================================
# BƯỚC 1: Cài đặt Desktop Environment (labwc/Wayland)
# =============================================================================
install_desktop() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 1: Cài đặt Desktop Environment (labwc)"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sudo apt-get update -y
    
    # Cài đặt labwc và các packages GUI cần thiết
    log "Cài đặt labwc Wayland compositor..."
    sudo apt-get install -y \
        labwc \
        lightdm \
        wf-panel-pi \
        pcmanfm \
        lxsession \
        xwayland \
        kanshi \
        2>&1 | tee -a "$LOG_FILE"
    
    # Cài đặt PyQt5 và các thư viện GUI
    log "Cài đặt PyQt5 và thư viện GUI..."
    sudo apt-get install -y \
        python3-pyqt5 \
        python3-pyqt5.qtquick \
        python3-pyqt5.qtmultimedia \
        qml-module-qtquick2 \
        qml-module-qtquick-controls \
        qml-module-qtquick-controls2 \
        qml-module-qtquick-layouts \
        qml-module-qtquick-window2 \
        qml-module-qtgraphicaleffects \
        qml-module-qtmultimedia \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        2>&1 | tee -a "$LOG_FILE"
    
    log "✓ Desktop Environment đã cài đặt"
}

# =============================================================================
# BƯỚC 2: Cài đặt Audio và Network
# =============================================================================
install_audio_network() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 2: Cài đặt Audio và Network packages"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sudo apt-get install -y \
        pulseaudio \
        pulseaudio-utils \
        alsa-utils \
        libportaudio2 \
        portaudio19-dev \
        libsndfile1 \
        libopus0 \
        libopus-dev \
        network-manager \
        2>&1 | tee -a "$LOG_FILE"
    
    # Thêm user vào group audio
    sudo usermod -aG audio $USER
    
    # Enable NetworkManager
    sudo systemctl enable NetworkManager
    sudo systemctl start NetworkManager 2>/dev/null || true
    
    log "✓ Audio và Network đã cài đặt"
}

# =============================================================================
# BƯỚC 3: Cài đặt Python dependencies
# =============================================================================
install_python_deps() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 3: Cài đặt Python dependencies"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sudo apt-get install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        2>&1 | tee -a "$LOG_FILE"
    
    # Cài đặt Python packages
    log "Cài đặt Python packages..."
    pip3 install --user --break-system-packages \
        sounddevice \
        numpy \
        aiohttp \
        websockets \
        qasync \
        sherpa-onnx \
        2>&1 | tee -a "$LOG_FILE" || \
    pip3 install --user \
        sounddevice \
        numpy \
        aiohttp \
        websockets \
        qasync \
        sherpa-onnx \
        2>&1 | tee -a "$LOG_FILE"
    
    log "✓ Python dependencies đã cài đặt"
}

# =============================================================================
# BƯỚC 4: Clone/Copy ứng dụng
# =============================================================================
install_app() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 4: Cài đặt Smart C AI"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Nếu đang chạy từ thư mục source
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        log "Copy files từ $SCRIPT_DIR..."
        mkdir -p "$INSTALL_DIR"
        rsync -av \
            --exclude='.git' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='build' \
            --exclude='dist' \
            --exclude='venv' \
            --exclude='logs/*.log' \
            "$SCRIPT_DIR/" "$INSTALL_DIR/"
    else
        # Clone từ GitHub
        log "Clone từ GitHub..."
        if [ -d "$INSTALL_DIR" ]; then
            cd "$INSTALL_DIR"
            git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || true
        else
        git clone https://github.com/digitsvn/digits-smart-c.git "$INSTALL_DIR" || {
                log_error "Không thể clone repo. Vui lòng copy files thủ công."
                return 1
            }
        fi
    fi
    
    # Tạo symlink
    if [ ! -L "$HOME/.xiaozhi" ]; then
        rm -rf "$HOME/.xiaozhi" 2>/dev/null || true
        ln -sf "$INSTALL_DIR" "$HOME/.xiaozhi"
        log "Tạo symlink ~/.xiaozhi -> ~/.digits"
    fi
    
    # Tạo thư mục logs và cache
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/cache"
    
    log "✓ Smart C AI đã cài đặt vào $INSTALL_DIR"
}

# =============================================================================
# BƯỚC 5: Cấu hình Desktop Autologin
# =============================================================================
configure_desktop_autologin() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 5: Cấu hình Desktop Autologin"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Sử dụng raspi-config để bật Desktop Autologin
    if command -v raspi-config &> /dev/null; then
        log "Cấu hình boot vào Desktop + Autologin..."
        sudo raspi-config nonint do_boot_behaviour B4
        log "✓ Desktop Autologin đã bật"
    else
        log_warn "raspi-config không có sẵn, cấu hình thủ công..."
        
        # Cấu hình LightDM autologin
        sudo mkdir -p /etc/lightdm/lightdm.conf.d/
        sudo tee /etc/lightdm/lightdm.conf.d/autologin.conf > /dev/null << EOF
[Seat:*]
autologin-user=$USER
autologin-user-timeout=0
EOF
        log "✓ LightDM autologin đã cấu hình"
    fi
}

# =============================================================================
# BƯỚC 6: Cấu hình autostart cho Smart C AI
# =============================================================================
configure_autostart() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 6: Cấu hình Autostart"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # =========================================
    # 1. Tạo run.sh launcher
    # =========================================
    cat > "$INSTALL_DIR/run.sh" << 'RUNEOF'
#!/bin/bash
# Smart C AI Launcher

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
    log "✓ Tạo run.sh launcher"
    
    # =========================================
    # 2. Autostart cho labwc (Raspberry Pi Wayland)
    # =========================================
    mkdir -p "$HOME/.config/labwc"
    
    # Tạo file autostart cho labwc
    cat > "$HOME/.config/labwc/autostart" << EOF
# Smart C AI - Auto start
$INSTALL_DIR/run.sh &
EOF
    
    chmod +x "$HOME/.config/labwc/autostart"
    log "✓ Cấu hình labwc autostart"
    
    # =========================================
    # 3. Autostart cho LXDE/LXQt/GNOME (desktop entry)
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
    
    log "✓ Cấu hình desktop autostart"
    
    # =========================================
    # 4. Autostart cho lxsession (Pi Desktop cũ)
    # =========================================
    mkdir -p "$HOME/.config/lxsession/LXDE-pi"
    
    # Thêm vào autostart của lxsession nếu chưa có
    LXSESSION_AUTOSTART="$HOME/.config/lxsession/LXDE-pi/autostart"
    if [ ! -f "$LXSESSION_AUTOSTART" ]; then
        touch "$LXSESSION_AUTOSTART"
    fi
    
    if ! grep -q "smartc" "$LXSESSION_AUTOSTART" 2>/dev/null; then
        echo "@$INSTALL_DIR/run.sh" >> "$LXSESSION_AUTOSTART"
        log "✓ Cấu hình lxsession autostart"
    fi
    
    # =========================================
    # 5. Tạo Desktop Shortcut (icon trên Desktop)
    # =========================================
    DESKTOP_DIR="$HOME/Desktop"
    [ ! -d "$DESKTOP_DIR" ] && DESKTOP_DIR="$HOME/Màn hình nền"
    [ ! -d "$DESKTOP_DIR" ] && mkdir -p "$HOME/Desktop" && DESKTOP_DIR="$HOME/Desktop"
    
    cat > "$DESKTOP_DIR/SmartC.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Comment=Trợ lý AI thông minh
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
Categories=Utility;
StartupNotify=true
EOF
    chmod +x "$DESKTOP_DIR/SmartC.desktop"
    log "✓ Tạo Desktop Shortcut: $DESKTOP_DIR/SmartC.desktop"
    
    # =========================================
    # 6. Copy icon vào system icons
    # =========================================
    mkdir -p "$HOME/.local/share/icons/hicolor/128x128/apps"
    cp "$INSTALL_DIR/assets/icon.png" "$HOME/.local/share/icons/hicolor/128x128/apps/smartc.png" 2>/dev/null || true
    log "✓ Icon đã copy vào ~/.local/share/icons"
    
    log "✓ Autostart đã cấu hình cho tất cả Desktop Environments"
}

# =============================================================================
# BƯỚC 7: Cấu hình ALSA cho audio
# =============================================================================
configure_audio() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 7: Cấu hình Audio"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Tạo ALSA config để hỗ trợ USB MIC
    cat > "$HOME/.asoundrc" << 'EOF'
# Smart C AI - ALSA Configuration

# Default PCM device - headphones
pcm.!default {
    type hw
    card Headphones
}

# Default control
ctl.!default {
    type hw
    card Headphones
}

# USB Microphone alias
pcm.usbmic {
    type hw
    card Device
}

# Headphones alias
pcm.headphones {
    type hw
    card Headphones
}
EOF
    
    # Set default volume
    amixer set Master 80% unmute 2>/dev/null || true
    amixer set PCM 80% unmute 2>/dev/null || true
    amixer set Headphone 80% unmute 2>/dev/null || true
    
    log "✓ Audio đã cấu hình"
}

# =============================================================================
# BƯỚC 8: Cấu hình NetworkManager cho WiFi Hotspot
# =============================================================================
configure_network() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 8: Cấu hình Network"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Cho phép user quản lý network không cần sudo
    if [ -d /etc/polkit-1/rules.d ]; then
        sudo tee /etc/polkit-1/rules.d/50-networkmanager.rules > /dev/null << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 && subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
EOF
        sudo usermod -aG netdev $USER
        log "✓ Network permissions đã cấu hình"
    fi
}

# =============================================================================
# HOÀN TẤT
# =============================================================================
print_complete() {
    echo
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║              ✅ CÀI ĐẶT HOÀN TẤT!                               ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}📍 Thông tin cài đặt:${NC}"
    echo -e "   Vị trí:     $INSTALL_DIR"
    echo -e "   Logs:       $INSTALL_DIR/logs/smartc.log"
    echo
    
    echo -e "${CYAN}🚀 Luồng hoạt động sau khi reboot:${NC}"
    echo -e "   1. Boot vào Desktop (labwc Wayland)"
    echo -e "   2. Smart C AI tự động khởi động"
    echo -e "   3. Nếu chưa có WiFi → Hiện Hotspot 'SmartC-Setup'"
    echo -e "   4. Cấu hình WiFi từ điện thoại"
    echo -e "   5. Cấu hình MIC/Loa trong Settings"
    echo -e "   6. Activation với Server"
    echo -e "   7. Vào Chat Bot - nói 'Alexa' hoặc 'Hey Lily'"
    echo
    
    echo -e "${YELLOW}⚠️  QUAN TRỌNG:${NC}"
    echo -e "   Reboot để áp dụng tất cả thay đổi!"
    echo
    
    echo -e "${GREEN}   sudo reboot${NC}"
    echo
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    print_banner
    
    check_root
    check_raspberry_pi
    
    log "Bắt đầu cài đặt Smart C AI..."
    log "Log file: $LOG_FILE"
    echo
    
    configure_display
    install_desktop
    install_audio_network
    install_python_deps
    install_app
    configure_desktop_autologin
    configure_autostart
    configure_audio
    configure_network
    
    print_complete
    
    echo -e "${YELLOW}Reboot ngay? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log "Rebooting..."
        sudo reboot
    fi
}

# Run
main "$@"
