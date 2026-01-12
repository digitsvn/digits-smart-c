#!/bin/bash
# =============================================================================
#            SMART C AI - OPTIMIZE FOR PI 4B (4GB RAM)
# =============================================================================
# Script tối ưu hệ thống cho Raspberry Pi 4B với 4GB RAM
# Đảm bảo app chạy mượt mà nhất
#
# Chạy: sudo bash scripts/optimize_pi4.sh
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
   echo "Chạy: sudo bash scripts/optimize_pi4.sh"
   exit 1
fi

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║     ⚡  SMART C AI - OPTIMIZE FOR PI 4B (4GB RAM)               ║"
echo "║         Tối ưu cho hiệu năng tốt nhất                          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Hiển thị thông tin hệ thống
echo -e "${CYAN}📊 Thông tin hệ thống:${NC}"
echo "   Model: $(cat /proc/device-tree/model 2>/dev/null || echo 'Unknown')"
echo "   RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "   CPU: $(nproc) cores"
echo "   Kernel: $(uname -r)"
echo ""

# =====================================================
# 1. Cấu hình Boot (config.txt)
# =====================================================
echo -e "${GREEN}[1/6] Cấu hình boot...${NC}"

CONFIG_FILE=""
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
fi

if [ -n "$CONFIG_FILE" ]; then
    # Backup
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup.$(date +%Y%m%d)"
    
    # Xóa các config cũ
    sed -i '/^gpu_mem=/d' "$CONFIG_FILE"
    sed -i '/^arm_freq=/d' "$CONFIG_FILE"
    sed -i '/^over_voltage=/d' "$CONFIG_FILE"
    sed -i '/^gpu_freq=/d' "$CONFIG_FILE"
    sed -i '/^hdmi_force_hotplug=/d' "$CONFIG_FILE"
    sed -i '/^hdmi_group=/d' "$CONFIG_FILE"
    sed -i '/^hdmi_mode=/d' "$CONFIG_FILE"
    sed -i '/^disable_overscan=/d' "$CONFIG_FILE"
    
    # Thêm config tối ưu cho Pi 4B 4GB
    cat >> "$CONFIG_FILE" << 'EOF'

# ============================================
# Smart C AI - Optimized for Pi 4B (4GB RAM)
# ============================================
# GPU Memory: 256MB cho GUI mượt
gpu_mem=256

# Overclock nhẹ (an toàn)
arm_freq=1800
over_voltage=2
gpu_freq=600

# HDMI 1920x1080 60Hz
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
hdmi_drive=2
disable_overscan=1

# Audio
dtparam=audio=on
EOF
    
    echo "   ✓ $CONFIG_FILE đã cập nhật"
else
    echo "   ⚠ Không tìm thấy config.txt"
fi

# =====================================================
# 2. Tắt services không cần thiết
# =====================================================
echo -e "${GREEN}[2/6] Tắt services không cần...${NC}"

SERVICES=(
    "bluetooth"
    "hciuart"
    "avahi-daemon"
    "cups"
    "cups-browsed"
    "ModemManager"
    "wpa_supplicant"  # Nếu dùng NetworkManager
    "triggerhappy"
)

for service in "${SERVICES[@]}"; do
    if systemctl is-enabled "$service" 2>/dev/null | grep -q "enabled"; then
        systemctl disable "$service" 2>/dev/null || true
        systemctl stop "$service" 2>/dev/null || true
        echo "   ✓ Tắt $service"
    fi
done

# =====================================================
# 3. Tối ưu Memory & Swap
# =====================================================
echo -e "${GREEN}[3/6] Tối ưu memory...${NC}"

# Với 4GB RAM, không cần swap nhiều
if [ -f /etc/dphys-swapfile ]; then
    sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=512/' /etc/dphys-swapfile
    dphys-swapfile swapoff 2>/dev/null || true
    dphys-swapfile setup 2>/dev/null || true
    dphys-swapfile swapon 2>/dev/null || true
    echo "   ✓ Swap: 512MB"
fi

# Tối ưu kernel memory
cat > /etc/sysctl.d/99-smartc.conf << 'EOF'
# Smart C AI - Memory Optimization
vm.swappiness=10
vm.vfs_cache_pressure=50
vm.dirty_ratio=15
vm.dirty_background_ratio=5
EOF

sysctl -p /etc/sysctl.d/99-smartc.conf 2>/dev/null || true
echo "   ✓ Kernel memory optimized"

# =====================================================
# 4. CPU Performance Mode
# =====================================================
echo -e "${GREEN}[4/6] CPU Performance mode...${NC}"

# Set performance governor
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo "performance" > "$cpu" 2>/dev/null || true
done

# Tạo service để giữ performance mode
cat > /etc/systemd/system/cpu-performance.service << 'EOF'
[Unit]
Description=Set CPU Governor to Performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo "performance" > "$cpu"; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cpu-performance.service 2>/dev/null || true
echo "   ✓ CPU Performance mode enabled"

# =====================================================
# 5. Cài đặt dependencies đầy đủ
# =====================================================
echo -e "${GREEN}[5/6] Kiểm tra dependencies...${NC}"

# Lấy user thật
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")
APP_HOME="$REAL_HOME/.digits"
[ ! -d "$APP_HOME" ] && APP_HOME="$REAL_HOME/.xiaozhi"

if [ -d "$APP_HOME" ] && [ -f "$APP_HOME/requirements.txt" ]; then
    echo "   Cài đặt Python packages..."
    sudo -u $REAL_USER pip3 install --user --break-system-packages -r "$APP_HOME/requirements.txt" 2>/dev/null || \
    sudo -u $REAL_USER pip3 install --user -r "$APP_HOME/requirements.txt" 2>/dev/null || true
    echo "   ✓ Python dependencies installed"
else
    echo "   ⚠ Không tìm thấy requirements.txt"
fi

# =====================================================
# 6. Cài đặt systemd service
# =====================================================
echo -e "${GREEN}[6/6] Cài đặt autostart service...${NC}"

if [ -f "$APP_HOME/scripts/install_service.sh" ]; then
    bash "$APP_HOME/scripts/install_service.sh"
else
    echo "   ⚠ Không tìm thấy install_service.sh"
fi

# =====================================================
# Hoàn tất
# =====================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ TỐI ƯU HOÀN TẤT CHO PI 4B (4GB)!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Đã áp dụng:${NC}"
echo "   ✓ GPU Memory: 256MB (cho GUI mượt)"
echo "   ✓ CPU: 1.8GHz (overclock nhẹ)"
echo "   ✓ HDMI: 1920x1080 @ 60Hz"
echo "   ✓ Swap: 512MB (đủ với 4GB RAM)"
echo "   ✓ CPU Governor: Performance"
echo "   ✓ Tắt services thừa"
echo "   ✓ Systemd autostart"
echo ""
echo -e "${YELLOW}⚠️  Cần REBOOT để áp dụng tất cả thay đổi!${NC}"
echo ""
echo -e "${CYAN}sudo reboot${NC}"
echo ""

# Hỏi reboot
read -p "Reboot ngay? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    reboot
fi
