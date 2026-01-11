#!/bin/bash
# =============================================================================
#            SMART C AI - MINIMAL INSTALLER (Pi OS Lite)
# =============================================================================
# Installer tối giản cho Pi OS Lite - KHÔNG cần Desktop
# Chỉ cài những gì cần thiết cho AI Chatbot hoạt động
#
# Chạy: bash install_minimal.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_NAME="smartc"
INSTALL_DIR="$HOME/.digits"
LOG_FILE="/tmp/smartc_minimal_install.log"

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║     🤖  SMART C AI - MINIMAL INSTALLER                          ║"
    echo "║         Phiên bản nhẹ nhất cho Pi OS Lite                       ║"
    echo "║         Chạy CLI mode - Không cần Desktop                       ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        echo -e "${RED}❌ Không chạy script này với sudo/root!${NC}"
        echo "Chạy lại: bash install_minimal.sh"
        exit 1
    fi
}

# =============================================================================
# BƯỚC 1: Cài đặt Audio (tối thiểu)
# =============================================================================
install_audio() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 1: Cài đặt Audio (tối thiểu)"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sudo apt-get update -y
    
    # Chỉ cài những gì cần thiết cho audio
    sudo apt-get install -y \
        alsa-utils \
        libportaudio2 \
        portaudio19-dev \
        libsndfile1 \
        libopus0 \
        libopus-dev \
        2>&1 | tee -a "$LOG_FILE"
    
    # Thêm user vào group audio
    sudo usermod -aG audio $USER
    
    log "✓ Audio đã cài đặt (ALSA only, không PulseAudio)"
}

# =============================================================================
# BƯỚC 2: Cài đặt Python dependencies
# =============================================================================
install_python_deps() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 2: Cài đặt Python dependencies"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    sudo apt-get install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        2>&1 | tee -a "$LOG_FILE"
    
    # Cài đặt Python packages (chỉ những gì cần thiết)
    log "Cài đặt Python packages..."
    pip3 install --user --break-system-packages \
        sounddevice \
        numpy \
        aiohttp \
        websockets \
        sherpa-onnx \
        2>&1 | tee -a "$LOG_FILE" || \
    pip3 install --user \
        sounddevice \
        numpy \
        aiohttp \
        websockets \
        sherpa-onnx \
        2>&1 | tee -a "$LOG_FILE"
    
    log "✓ Python dependencies đã cài đặt"
}

# =============================================================================
# BƯỚC 3: Clone/Copy ứng dụng
# =============================================================================
install_app() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 3: Cài đặt Smart C AI"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Nếu đang chạy từ thư mục source
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        log "Copy files từ $SCRIPT_DIR..."
        mkdir -p "$INSTALL_DIR"
        
        # Copy chỉ những file cần thiết
        rsync -av \
            --exclude='.git' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='build' \
            --exclude='dist' \
            --exclude='venv' \
            --exclude='logs/*.log' \
            --exclude='.agent' \
            --exclude='plans' \
            "$SCRIPT_DIR/" "$INSTALL_DIR/"
    else
        # Clone từ GitHub
        log "Clone từ GitHub..."
        if [ -d "$INSTALL_DIR" ]; then
            cd "$INSTALL_DIR"
            git pull origin main 2>/dev/null || true
        else
            git clone https://github.com/nguyenduchoai/py-xiaozhi-pi.git "$INSTALL_DIR" || {
                echo -e "${RED}❌ Không thể clone repo${NC}"
                return 1
            }
        fi
    fi
    
    # Tạo thư mục cần thiết
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/cache"
    
    log "✓ Smart C AI đã cài đặt vào $INSTALL_DIR"
}

# =============================================================================
# BƯỚC 4: Tạo CLI launcher
# =============================================================================
create_launcher() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 4: Tạo CLI launcher"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cat > "$INSTALL_DIR/run_cli.sh" << 'EOF'
#!/bin/bash
# Smart C AI - CLI Mode (Minimal)

APP_HOME="$HOME/.digits"
cd "$APP_HOME"
mkdir -p logs

echo "$(date): Smart C AI starting (CLI mode)..." >> logs/smartc.log

# Ensure device ID
python3 "$APP_HOME/scripts/ensure_device_id_mac.py" 2>/dev/null || true

# Stop existing instance
pkill -f "python3 main.py" 2>/dev/null
sleep 0.5

echo "🚀 Starting Smart C AI (CLI mode)..."
exec python3 main.py --mode cli 2>&1 | tee -a logs/smartc.log
EOF
    
    chmod +x "$INSTALL_DIR/run_cli.sh"
    log "✓ CLI launcher đã tạo"
}

# =============================================================================
# BƯỚC 5: Tạo systemd service
# =============================================================================
create_service() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 5: Tạo systemd service"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Tạo service file
    sudo tee /etc/systemd/system/smartc.service > /dev/null << EOF
[Unit]
Description=Smart C AI Voice Assistant
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/main.py --mode cli
Restart=on-failure
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/smartc.log
StandardError=append:$INSTALL_DIR/logs/smartc.log

# Giới hạn tài nguyên để tối ưu
MemoryMax=512M
CPUQuota=80%

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload và enable service
    sudo systemctl daemon-reload
    sudo systemctl enable smartc.service
    
    log "✓ systemd service đã tạo và enable"
}

# =============================================================================
# BƯỚC 6: Cấu hình ALSA
# =============================================================================
configure_audio() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 6: Cấu hình Audio"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Tạo ALSA config đơn giản
    cat > "$HOME/.asoundrc" << 'EOF'
# Smart C AI - ALSA Configuration (Minimal)

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

# USB Microphone
pcm.usbmic {
    type hw
    card Device
}
EOF
    
    # Set volume
    amixer set Master 80% unmute 2>/dev/null || true
    
    log "✓ Audio đã cấu hình"
}

# =============================================================================
# HOÀN TẤT
# =============================================================================
print_complete() {
    echo
    echo -e "${GREEN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║              ✅ CÀI ĐẶT TỐI GIẢN HOÀN TẤT!                       ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}📍 Thông tin:${NC}"
    echo "   Vị trí:     $INSTALL_DIR"
    echo "   Mode:       CLI (không cần Desktop)"
    echo "   Service:    smartc.service"
    echo
    
    echo -e "${CYAN}🚀 Cách sử dụng:${NC}"
    echo
    echo "   # Khởi động service"
    echo "   sudo systemctl start smartc"
    echo
    echo "   # Xem trạng thái"
    echo "   sudo systemctl status smartc"
    echo
    echo "   # Xem logs"
    echo "   tail -f ~/.digits/logs/smartc.log"
    echo
    echo "   # Dừng service"
    echo "   sudo systemctl stop smartc"
    echo
    echo "   # Chạy thủ công (debug)"
    echo "   ~/.digits/run_cli.sh"
    echo
    
    echo -e "${YELLOW}⚠️  LƯU Ý:${NC}"
    echo "   - Service sẽ tự động chạy khi boot"
    echo "   - Sử dụng Wake Word để bắt đầu nói chuyện"
    echo "   - Nói 'Alexa', 'Hey Lily', hoặc 'Smart C' để kích hoạt"
    echo
    
    echo -e "${GREEN}   Khởi động ngay: sudo systemctl start smartc${NC}"
    echo
}

# =============================================================================
# RAM/CPU tối ưu
# =============================================================================
optimize_system() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "BƯỚC 7: Tối ưu hệ thống"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Tắt các service không cần thiết
    sudo systemctl disable bluetooth 2>/dev/null || true
    sudo systemctl stop bluetooth 2>/dev/null || true
    
    # Tắt avahi (mDNS)
    sudo systemctl disable avahi-daemon 2>/dev/null || true
    sudo systemctl stop avahi-daemon 2>/dev/null || true
    
    # Tắt triggerhappy (hotkey daemon)
    sudo systemctl disable triggerhappy 2>/dev/null || true
    sudo systemctl stop triggerhappy 2>/dev/null || true
    
    # Giảm GPU memory (nếu không dùng màn hình)
    if ! grep -q "gpu_mem=16" /boot/config.txt 2>/dev/null && \
       ! grep -q "gpu_mem=16" /boot/firmware/config.txt 2>/dev/null; then
        if [ -f /boot/firmware/config.txt ]; then
            echo "gpu_mem=16" | sudo tee -a /boot/firmware/config.txt > /dev/null
        elif [ -f /boot/config.txt ]; then
            echo "gpu_mem=16" | sudo tee -a /boot/config.txt > /dev/null
        fi
        log "✓ Giảm GPU memory xuống 16MB"
    fi
    
    log "✓ Đã tắt các service không cần thiết"
}

# =============================================================================
# MAIN
# =============================================================================
main() {
    print_banner
    check_root
    
    log "Bắt đầu cài đặt tối giản Smart C AI..."
    log "Log file: $LOG_FILE"
    echo
    
    install_audio
    install_python_deps
    install_app
    create_launcher
    configure_audio
    create_service
    optimize_system
    
    print_complete
    
    echo -e "${YELLOW}Khởi động service ngay? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo systemctl start smartc
        log "Service đã khởi động!"
        echo
        echo "Xem logs: tail -f ~/.digits/logs/smartc.log"
    fi
}

# Run
main "$@"
