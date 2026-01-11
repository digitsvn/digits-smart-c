#!/bin/bash
# =============================================================================
#                    SMART C AI - ONE-CLICK INSTALLER
# =============================================================================
#
# Script này sẽ:
# 1. Cài đặt tất cả dependencies cần thiết
# 2. Cài đặt ứng dụng vào ~/.digits
# 3. Tạo desktop icon và menu entry
# 4. Cấu hình audio và network
# 5. Thiết lập autostart (optional)
#
# Chạy: bash setup.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Config
APP_NAME="smartc"
APP_DISPLAY="Smart C AI"
VERSION="1.0.0"
INSTALL_DIR="$HOME/.digits"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                  ║"
    echo "║     🤖  SMART C AI - Trợ lý AI thông minh                       ║"
    echo "║                                                                  ║"
    echo "║     Phiên bản: ${VERSION}                                            ║"
    echo "║     Website: https://xiaozhi-ai-iot.vn                           ║"
    echo "║                                                                  ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}[STEP]${NC} $1"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

log_info() {
    echo -e "${YELLOW}  →${NC} $1"
}

log_success() {
    echo -e "${GREEN}  ✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}  ⚠${NC} $1"
}

log_error() {
    echo -e "${RED}  ✗${NC} $1"
}

# Check if running as root
check_not_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "Không chạy script này với sudo!"
        log_info "Chạy lại: bash setup.sh"
        exit 1
    fi
}

# Check if Raspberry Pi
is_raspberry_pi() {
    if [ -f /proc/device-tree/model ]; then
        grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null && return 0
    fi
    return 1
}

# Install system dependencies
install_system_deps() {
    log_step "Cài đặt System Dependencies"
    
    log_info "Cập nhật package list..."
    sudo apt-get update -y
    
    log_info "Cài đặt dependencies..."
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-pyqt5 \
        python3-pyqt5.qtquick \
        libportaudio2 \
        portaudio19-dev \
        libsndfile1 \
        alsa-utils \
        pulseaudio \
        pulseaudio-utils \
        network-manager \
        libopus0 \
        libopus-dev \
        2>/dev/null || log_warning "Một số packages có thể đã được cài"
    
    log_success "System dependencies đã cài đặt"
}

# Install Python dependencies
install_python_deps() {
    log_step "Cài đặt Python Dependencies"
    
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        log_info "Cài đặt từ requirements.txt..."
        pip3 install --user -r "$SCRIPT_DIR/requirements.txt" --break-system-packages 2>/dev/null || \
        pip3 install --user -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || \
        log_warning "Một số packages có thể đã được cài"
    else
        log_info "Cài đặt packages cơ bản..."
        pip3 install --user \
            sounddevice \
            numpy \
            aiohttp \
            websockets \
            qasync \
            --break-system-packages 2>/dev/null || \
        pip3 install --user sounddevice numpy aiohttp websockets qasync
    fi
    
    log_success "Python dependencies đã cài đặt"
}

# Copy files to install directory
copy_files() {
    log_step "Cài đặt ứng dụng vào $INSTALL_DIR"
    
    log_info "Tạo thư mục cài đặt..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/config"
    
    log_info "Copy files..."
    rsync -av \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='build' \
        --exclude='dist' \
        --exclude='venv' \
        --exclude='.vscode' \
        --exclude='*.egg-info' \
        --exclude='.pytest_cache' \
        "$SCRIPT_DIR/" "$INSTALL_DIR/"
    
    # Tạo symlink cho backward compatibility
    if [ ! -L "$HOME/.xiaozhi" ]; then
        rm -rf "$HOME/.xiaozhi" 2>/dev/null || true
        ln -sf "$INSTALL_DIR" "$HOME/.xiaozhi"
        log_info "Tạo symlink ~/.xiaozhi -> ~/.digits"
    fi
    
    log_success "Files đã được copy"
}

# Create launcher script
create_launcher() {
    log_step "Tạo Launcher Script"
    
    cat > "$INSTALL_DIR/run.sh" << 'EOF'
#!/bin/bash
# Smart C AI Launcher

cd "$HOME/.digits"
mkdir -p logs

# Start PulseAudio if not running
if ! pulseaudio --check 2>/dev/null; then
    pulseaudio --start --daemonize=true 2>/dev/null || true
fi

# Run the application
exec python3 main.py --mode gui "$@" 2>&1 | tee -a logs/smartc.log
EOF
    
    chmod +x "$INSTALL_DIR/run.sh"
    log_success "Launcher script đã tạo"
}

# Create desktop entries
create_desktop_entries() {
    log_step "Tạo Desktop Icon & Menu Entry"
    
    # Desktop entry directory
    mkdir -p "$HOME/.local/share/applications"
    mkdir -p "$HOME/Desktop"
    
    # Find icon
    ICON_PATH="$INSTALL_DIR/assets/icon.png"
    if [ ! -f "$ICON_PATH" ]; then
        ICON_PATH="applications-other"
    fi
    
    # Create .desktop file
    cat > "$HOME/.local/share/applications/smartc.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_DISPLAY
GenericName=Trợ lý AI
Comment=Trợ lý AI thông minh cho Raspberry Pi
Exec=$INSTALL_DIR/run.sh
Icon=$ICON_PATH
Terminal=false
Categories=Audio;AudioVideo;Utility;Network;
StartupNotify=true
Keywords=voice;ai;assistant;smartc;xiaozhi;
Actions=settings;logs;

[Desktop Action settings]
Name=Mở Settings
Exec=$INSTALL_DIR/run.sh --settings

[Desktop Action logs]
Name=Xem Logs
Exec=xdg-open $INSTALL_DIR/logs/smartc.log
EOF
    
    # Copy to Desktop
    cp "$HOME/.local/share/applications/smartc.desktop" "$HOME/Desktop/" 2>/dev/null || true
    chmod +x "$HOME/Desktop/smartc.desktop" 2>/dev/null || true
    
    # Trust desktop file
    if command -v gio &> /dev/null; then
        gio set "$HOME/Desktop/smartc.desktop" metadata::trusted true 2>/dev/null || true
    fi
    
    log_success "Desktop entries đã tạo"
}

# Create terminal command
create_terminal_command() {
    log_step "Tạo lệnh Terminal"
    
    mkdir -p "$HOME/.local/bin"
    ln -sf "$INSTALL_DIR/run.sh" "$HOME/.local/bin/smartc"
    
    # Add to PATH if not already
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        log_info "Đã thêm ~/.local/bin vào PATH"
    fi
    
    log_success "Lệnh 'smartc' đã được tạo"
}

# Configure audio
configure_audio() {
    log_step "Cấu hình Audio"
    
    # Add user to audio group
    sudo usermod -aG audio $USER 2>/dev/null || true
    log_info "Đã thêm user vào group 'audio'"
    
    # Set default volume
    amixer set Master 80% unmute 2>/dev/null || true
    amixer set PCM 80% unmute 2>/dev/null || true
    amixer set Headphone 80% unmute 2>/dev/null || true
    amixer set Capture 80% cap 2>/dev/null || true
    log_info "Đã thiết lập âm lượng mặc định"
    
    log_success "Audio đã được cấu hình"
}

# Configure network
configure_network() {
    log_step "Cấu hình Network"
    
    # Enable NetworkManager
    if systemctl is-active --quiet NetworkManager; then
        log_info "NetworkManager đang chạy"
    else
        log_info "Bật NetworkManager..."
        sudo systemctl enable NetworkManager 2>/dev/null || true
        sudo systemctl start NetworkManager 2>/dev/null || true
    fi
    
    # Allow user to manage network without sudo
    if [ -d /etc/polkit-1/rules.d ]; then
        sudo tee /etc/polkit-1/rules.d/50-networkmanager.rules > /dev/null 2>&1 << 'EOF' || true
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") == 0 && subject.isInGroup("netdev")) {
        return polkit.Result.YES;
    }
});
EOF
        sudo usermod -aG netdev $USER 2>/dev/null || true
        log_info "Đã cấu hình quyền network"
    fi
    
    log_success "Network đã được cấu hình"
}

# Setup autostart
setup_autostart() {
    log_step "Thiết lập Autostart"
    
    echo -e "${YELLOW}Bạn có muốn Smart C AI tự động chạy khi khởi động? (y/n)${NC}"
    read -r -p "> " response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        mkdir -p "$HOME/.config/autostart"
        cat > "$HOME/.config/autostart/smartc.desktop" << EOF
[Desktop Entry]
Type=Application
Name=$APP_DISPLAY
Exec=$INSTALL_DIR/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Start Smart C AI on login
EOF
        log_success "Autostart đã được bật"
    else
        rm -f "$HOME/.config/autostart/smartc.desktop" 2>/dev/null || true
        log_info "Autostart không được bật"
    fi
}

# Print completion message
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
    echo -e "   Config:     $INSTALL_DIR/config/config.json"
    echo -e "   Logs:       $INSTALL_DIR/logs/smartc.log"
    echo
    
    echo -e "${CYAN}🚀 Cách chạy ứng dụng:${NC}"
    echo -e "   ${YELLOW}1.${NC} Double-click icon ${MAGENTA}Smart C AI${NC} trên Desktop"
    echo -e "   ${YELLOW}2.${NC} Tìm trong menu Applications → Smart C AI"
    echo -e "   ${YELLOW}3.${NC} Terminal: ${GREEN}smartc${NC} (sau khi logout/login)"
    echo -e "   ${YELLOW}4.${NC} Trực tiếp: ${GREEN}$INSTALL_DIR/run.sh${NC}"
    echo
    
    echo -e "${CYAN}🎤 Lần đầu sử dụng:${NC}"
    echo -e "   1. Cấu hình WiFi (nếu chưa có kết nối)"
    echo -e "   2. Chọn thiết bị MIC và Loa trong Settings"
    echo -e "   3. Kích hoạt thiết bị với server"
    echo -e "   4. Nói \"Alexa\" hoặc \"Hey Lily\" để bắt đầu"
    echo
    
    echo -e "${CYAN}📖 Hỗ trợ:${NC}"
    echo -e "   Website:    https://xiaozhi-ai-iot.vn"
    echo -e "   Kiểm tra:   python3 $INSTALL_DIR/scripts/check_audio_wifi.py"
    echo
    
    echo -e "${YELLOW}⚠️  Lưu ý: Khởi động lại hoặc logout/login để áp dụng tất cả thay đổi${NC}"
    echo
    
    echo -e "${GREEN}Khởi động ngay bây giờ? (y/n)${NC}"
    read -r -p "> " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Khởi động Smart C AI...${NC}"
        "$INSTALL_DIR/run.sh" &
    fi
}

# Main installation flow
main() {
    print_banner
    
    check_not_root
    
    echo -e "${YELLOW}Bắt đầu cài đặt Smart C AI...${NC}"
    echo -e "${YELLOW}Quá trình này có thể mất vài phút.${NC}"
    echo
    
    install_system_deps
    install_python_deps
    copy_files
    create_launcher
    create_desktop_entries
    create_terminal_command
    configure_audio
    configure_network
    setup_autostart
    
    print_complete
}

# Run
main "$@"
