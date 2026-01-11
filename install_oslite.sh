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
        qml-module-qtquick2 \
        qml-module-qtquick-controls \
        qml-module-qtquick-controls2 \
        qml-module-qtquick-layouts \
        qml-module-qtquick-window2 \
        qml-module-qtgraphicaleffects \
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
        git clone https://github.com/nguyenduchoai/py-xiaozhi-pi.git "$INSTALL_DIR" || {
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
    
    mkdir -p "$HOME/.config/autostart"
    
    # Tạo desktop entry cho autostart
    cat > "$HOME/.config/autostart/smartc.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Comment=Trợ lý AI thông minh
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF
    
    # Tạo run.sh launcher
    cat > "$INSTALL_DIR/run.sh" << 'RUNEOF'
#!/bin/bash
# Smart C AI Launcher

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

cd "$APP_HOME"
mkdir -p logs

# Detect display environment
if [ -n "$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM=wayland
elif [ -n "$DISPLAY" ]; then
    export QT_QPA_PLATFORM=xcb
else
    # Try to find Wayland socket
    WAYLAND_SOCK=$(ls /run/user/$(id -u)/wayland-* 2>/dev/null | head -1)
    if [ -n "$WAYLAND_SOCK" ]; then
        export WAYLAND_DISPLAY=$(basename "$WAYLAND_SOCK")
        export QT_QPA_PLATFORM=wayland
    else
        export DISPLAY=:0
        export QT_QPA_PLATFORM=xcb
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

echo "🚀 Starting Smart C AI..."
exec python3 main.py --mode gui 2>&1 | tee -a logs/smartc.log
RUNEOF
    
    chmod +x "$INSTALL_DIR/run.sh"
    
    log "✓ Autostart đã cấu hình"
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
