#!/bin/bash
# =============================================================================
# Smart C - Script cài đặt cho Raspberry Pi OS Lite
# =============================================================================
# 
# Script này sẽ:
# 1. Cài đặt các dependencies cần thiết
# 2. Cấu hình audio (ALSA, PulseAudio)
# 3. Cấu hình NetworkManager cho WiFi hotspot
# 4. Thiết lập autostart
#
# Chạy: sudo bash install_pi.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check root
if [[ $EUID -ne 0 ]]; then
   log_error "Script này cần chạy với quyền root (sudo)"
   exit 1
fi

# Xác định user thực (không phải root)
ACTUAL_USER=${SUDO_USER:-$USER}
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

log_info "Cài đặt cho user: $ACTUAL_USER"
log_info "Home directory: $ACTUAL_HOME"

echo ""
echo "=============================================="
echo "   SMART C - CÀI ĐẶT CHO RASPBERRY PI"
echo "=============================================="
echo ""

# =============================================================================
# 1. Cập nhật hệ thống
# =============================================================================
log_info "Bước 1: Cập nhật hệ thống..."

apt-get update -y
apt-get upgrade -y

log_success "Hệ thống đã được cập nhật"

# =============================================================================
# 2. Cài đặt dependencies
# =============================================================================
log_info "Bước 2: Cài đặt dependencies..."

# Audio dependencies
apt-get install -y \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libsndfile1

# Network dependencies
apt-get install -y \
    network-manager \
    dnsmasq-base \
    hostapd

# Python dependencies
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-pyqt5 \
    python3-pyqt5.qtquick

# Build tools
apt-get install -y \
    build-essential \
    cmake \
    git

# Opus codec
apt-get install -y \
    libopus0 \
    libopus-dev \
    opus-tools

log_success "Dependencies đã được cài đặt"

# =============================================================================
# 3. Cấu hình NetworkManager
# =============================================================================
log_info "Bước 3: Cấu hình NetworkManager..."

# Enable NetworkManager
systemctl enable NetworkManager
systemctl start NetworkManager

# Disable old network config if exists
if [ -f /etc/dhcpcd.conf ]; then
    log_info "Vô hiệu hóa dhcpcd..."
    systemctl disable dhcpcd 2>/dev/null || true
    systemctl stop dhcpcd 2>/dev/null || true
fi

# Configure WiFi country
raspi-config nonint do_wifi_country VN 2>/dev/null || true

log_success "NetworkManager đã được cấu hình"

# =============================================================================
# 4. Cấu hình Audio
# =============================================================================
log_info "Bước 4: Cấu hình Audio..."

# Thêm user vào group audio
usermod -aG audio $ACTUAL_USER

# Tạo cấu hình ALSA mặc định nếu chưa có
ASOUND_CONF="$ACTUAL_HOME/.asoundrc"
if [ ! -f "$ASOUND_CONF" ]; then
    log_info "Tạo cấu hình ALSA mặc định..."
    cat > "$ASOUND_CONF" << 'EOF'
# ALSA configuration for Smart C
# Sử dụng card mặc định

pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:1,0"
    }
}

ctl.!default {
    type hw
    card 0
}
EOF
    chown $ACTUAL_USER:$ACTUAL_USER "$ASOUND_CONF"
fi

# Đảm bảo âm lượng không bị mute
log_info "Thiết lập âm lượng mặc định..."
amixer set Master 80% unmute 2>/dev/null || true
amixer set PCM 80% unmute 2>/dev/null || true
amixer set Headphone 80% unmute 2>/dev/null || true
amixer set Capture 80% cap 2>/dev/null || true

log_success "Audio đã được cấu hình"

# =============================================================================
# 5. Cài đặt Python packages
# =============================================================================
log_info "Bước 5: Cài đặt Python packages..."

INSTALL_DIR="$ACTUAL_HOME/.digits"

if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    log_info "Cài đặt từ requirements.txt..."
    sudo -u $ACTUAL_USER pip3 install --user -r "$INSTALL_DIR/requirements.txt"
else
    log_info "Cài đặt packages cơ bản..."
    sudo -u $ACTUAL_USER pip3 install --user \
        sounddevice \
        numpy \
        aiohttp \
        websockets \
        PyQt5 \
        qasync \
        sherpa-onnx
fi

log_success "Python packages đã được cài đặt"

# =============================================================================
# 6. Thiết lập Autostart
# =============================================================================
log_info "Bước 6: Thiết lập Autostart..."

AUTOSTART_DIR="$ACTUAL_HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
chown -R $ACTUAL_USER:$ACTUAL_USER "$ACTUAL_HOME/.config"

DESKTOP_FILE="$AUTOSTART_DIR/smartc.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Comment=Trợ lý AI Smart C
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

chown $ACTUAL_USER:$ACTUAL_USER "$DESKTOP_FILE"

# Tạo systemd service cho headless mode
SERVICE_FILE="/etc/systemd/system/smartc.service"
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Smart C AI Assistant
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$INSTALL_DIR
Environment="DISPLAY=:0"
Environment="PULSE_SERVER=unix:/run/user/$(id -u $ACTUAL_USER)/pulse/native"
ExecStart=/usr/bin/python3 $INSTALL_DIR/main.py --mode cli
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

log_success "Autostart đã được thiết lập"

# =============================================================================
# 7. Tạo script khởi động
# =============================================================================
log_info "Bước 7: Tạo script khởi động..."

RUN_SCRIPT="$INSTALL_DIR/run.sh"
cat > "$RUN_SCRIPT" << EOF
#!/bin/bash
# Smart C - Script khởi động

cd "$INSTALL_DIR"

# Đợi network
sleep 5

# Kiểm tra và khởi động PulseAudio nếu cần
if ! pulseaudio --check 2>/dev/null; then
    pulseaudio --start --daemonize=true 2>/dev/null || true
fi

# Chạy ứng dụng
exec python3 main.py --mode gui
EOF

chmod +x "$RUN_SCRIPT"
chown $ACTUAL_USER:$ACTUAL_USER "$RUN_SCRIPT"

log_success "Script khởi động đã được tạo"

# =============================================================================
# 8. Cấu hình permissions
# =============================================================================
log_info "Bước 8: Cấu hình permissions..."

# Cho phép user sử dụng nmcli không cần sudo
cat > /etc/polkit-1/rules.d/50-networkmanager.rules << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 && subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
EOF

# Thêm user vào group netdev
usermod -aG netdev $ACTUAL_USER

log_success "Permissions đã được cấu hình"

# =============================================================================
# Hoàn tất
# =============================================================================
echo ""
echo "=============================================="
echo "   CÀI ĐẶT HOÀN TẤT!"
echo "=============================================="
echo ""
log_success "Smart C đã được cài đặt thành công!"
echo ""
echo "Các bước tiếp theo:"
echo "  1. Khởi động lại Raspberry Pi: sudo reboot"
echo "  2. Kết nối WiFi nếu chưa có"
echo "  3. Chạy ứng dụng: $INSTALL_DIR/run.sh"
echo ""
echo "Để chạy như service (headless):"
echo "  sudo systemctl enable smartc"
echo "  sudo systemctl start smartc"
echo ""
echo "Kiểm tra audio/wifi:"
echo "  python3 $INSTALL_DIR/scripts/check_audio_wifi.py"
echo ""
log_info "Khởi động lại để áp dụng tất cả thay đổi..."
echo ""
