#!/bin/bash
# =============================================================================
#            SMART C AI - INSTALL SYSTEMD SERVICE
# =============================================================================
# Script này cài đặt systemd service để app TỰ ĐỘNG CHẠY khi boot
# ĐẢM BẢO HOẠT ĐỘNG trên mọi loại Pi
#
# Chạy: sudo bash scripts/install_service.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Kiểm tra root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Script này cần chạy với sudo!${NC}"
   echo "Chạy: sudo bash scripts/install_service.sh"
   exit 1
fi

# Lấy user thật (không phải root)
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

APP_HOME="$REAL_HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$REAL_HOME/.xiaozhi"
fi

if [ ! -d "$APP_HOME" ]; then
    echo -e "${RED}❌ Không tìm thấy thư mục Smart C AI${NC}"
    exit 1
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     🚀  SMART C AI - INSTALL SYSTEMD SERVICE                    ║"
echo "║         Tự động chạy khi boot - ĐẢM BẢO HOẠT ĐỘNG              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "📁 App directory: $APP_HOME"
echo "👤 User: $REAL_USER"
echo ""

# =====================================================
# 1. Tạo launcher script (chạy dưới user thường)
# =====================================================
echo -e "${GREEN}[1/4] Tạo launcher script...${NC}"

cat > "$APP_HOME/start_service.sh" << 'LAUNCHER'
#!/bin/bash
# Smart C AI - Service Launcher

export HOME="/home/$(whoami)"
export USER="$(whoami)"
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"

APP_HOME="$HOME/.digits"
[ ! -d "$APP_HOME" ] && APP_HOME="$HOME/.xiaozhi"

cd "$APP_HOME" || exit 1
mkdir -p logs

LOG="$APP_HOME/logs/service.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a "$LOG"
}

log "=========================================="
log "🚀 Smart C AI Service Starting..."
log "User: $USER, Home: $HOME"

# Đợi hệ thống sẵn sàng
sleep 10

# Setup XDG
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

# Tìm display
find_display() {
    # Thử Wayland trước
    for sock in "$XDG_RUNTIME_DIR"/wayland-*; do
        if [ -S "$sock" ] 2>/dev/null; then
            export WAYLAND_DISPLAY=$(basename "$sock")
            export QT_QPA_PLATFORM=wayland
            log "Found Wayland: $WAYLAND_DISPLAY"
            return 0
        fi
    done
    
    # Thử X11
    if [ -e /tmp/.X11-unix/X0 ]; then
        export DISPLAY=:0
        export QT_QPA_PLATFORM=xcb
        log "Found X11: $DISPLAY"
        return 0
    fi
    
    # Không có display -> dùng CLI mode
    log "No display found, using CLI mode"
    return 1
}

# Khởi động PulseAudio
start_audio() {
    if command -v pulseaudio &> /dev/null; then
        if ! pulseaudio --check 2>/dev/null; then
            log "Starting PulseAudio..."
            pulseaudio --start --daemonize=true 2>/dev/null || true
            sleep 2
        fi
    fi
}

# Kill TẤT CẢ instances cũ (quan trọng!)
log "Killing old instances..."
pkill -9 -f "python3 main.py" 2>/dev/null || true
pkill -9 -f "python3 $APP_HOME/main.py" 2>/dev/null || true
sleep 2

# Double check
pgrep -f "python3 main.py" && {
    log "Force killing remaining instances..."
    pkill -9 -f "python3 main.py" 2>/dev/null || true
    sleep 1
}

# Setup
start_audio

# Chọn mode
if find_display; then
    MODE="gui"
else
    MODE="cli"
fi

log "Starting in $MODE mode..."
log "QT_QPA_PLATFORM: $QT_QPA_PLATFORM"
log "DISPLAY: $DISPLAY"
log "WAYLAND_DISPLAY: $WAYLAND_DISPLAY"

# Chạy app
exec python3 main.py --mode $MODE 2>&1 | tee -a "$LOG"
LAUNCHER

chmod +x "$APP_HOME/start_service.sh"
chown $REAL_USER:$REAL_USER "$APP_HOME/start_service.sh"
echo "   ✓ $APP_HOME/start_service.sh"

# =====================================================
# 2. Tạo systemd service
# =====================================================
echo -e "${GREEN}[2/4] Tạo systemd service...${NC}"

cat > /etc/systemd/system/smartc.service << EOF
[Unit]
Description=Smart C AI Voice Assistant
Documentation=https://github.com/digitsvn/digits-smart-c
After=network-online.target sound.target graphical.target
Wants=network-online.target sound.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$APP_HOME
ExecStart=$APP_HOME/start_service.sh
Restart=on-failure
RestartSec=10
TimeoutStartSec=120
TimeoutStopSec=30

# Environment
Environment="HOME=$REAL_HOME"
Environment="USER=$REAL_USER"
Environment="PATH=$REAL_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Resource limits (tối ưu cho Pi)
MemoryMax=512M
CPUQuota=80%

# Logging
StandardOutput=append:$APP_HOME/logs/service.log
StandardError=append:$APP_HOME/logs/service.log

[Install]
WantedBy=multi-user.target
EOF

echo "   ✓ /etc/systemd/system/smartc.service"

# =====================================================
# 3. Enable và start service
# =====================================================
echo -e "${GREEN}[3/4] Enable service...${NC}"

# Tạo thư mục logs
mkdir -p "$APP_HOME/logs"
chown -R $REAL_USER:$REAL_USER "$APP_HOME/logs"

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable smartc.service

echo "   ✓ Service enabled"

# =====================================================
# 4. Kiểm tra và khởi động
# =====================================================
echo -e "${GREEN}[4/4] Khởi động service...${NC}"

# Stop nếu đang chạy
systemctl stop smartc.service 2>/dev/null || true
sleep 2

# Start service
systemctl start smartc.service

# Chờ và kiểm tra
sleep 5

if systemctl is-active --quiet smartc.service; then
    STATUS="${GREEN}✓ RUNNING${NC}"
else
    STATUS="${YELLOW}⚠ STARTING...${NC}"
fi

# =====================================================
# Done
# =====================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ SERVICE ĐÃ CÀI ĐẶT!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "📍 Status: $STATUS"
echo ""
echo -e "${CYAN}Commands:${NC}"
echo "   sudo systemctl status smartc     # Xem trạng thái"
echo "   sudo systemctl restart smartc    # Restart"
echo "   sudo systemctl stop smartc       # Dừng"
echo "   sudo journalctl -u smartc -f     # Xem logs"
echo ""
echo -e "${CYAN}Logs:${NC}"
echo "   tail -f $APP_HOME/logs/service.log"
echo ""
echo -e "${YELLOW}App sẽ TỰ ĐỘNG CHẠY mỗi khi bật Pi!${NC}"
echo ""

# Hiển thị status
systemctl status smartc.service --no-pager || true
