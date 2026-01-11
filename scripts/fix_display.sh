#!/bin/bash
# =============================================================================
#            SMART C AI - FIX DISPLAY (Full HD 1920x1080)
# =============================================================================
# Script này cấu hình HDMI output Full HD cho Raspberry Pi
# Chạy: sudo bash scripts/fix_display.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Kiểm tra root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ Script này cần chạy với sudo!${NC}"
   echo "Chạy: sudo bash scripts/fix_display.sh"
   exit 1
fi

echo -e "${GREEN}🖥️  Cấu hình HDMI Display - Full HD 1920x1080${NC}"
echo

# Xác định file config.txt
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
else
    echo -e "${RED}❌ Không tìm thấy config.txt${NC}"
    exit 1
fi

echo "📁 Config file: $CONFIG_FILE"

# Backup
BACKUP_FILE="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CONFIG_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup: $BACKUP_FILE${NC}"

# Xóa cấu hình HDMI cũ
sed -i '/^hdmi_group=/d' "$CONFIG_FILE"
sed -i '/^hdmi_mode=/d' "$CONFIG_FILE"
sed -i '/^hdmi_force_hotplug=/d' "$CONFIG_FILE"
sed -i '/^disable_overscan=/d' "$CONFIG_FILE"
sed -i '/^hdmi_drive=/d' "$CONFIG_FILE"
sed -i '/^hdmi_blanking=/d' "$CONFIG_FILE"

# Menu chọn độ phân giải
echo
echo "Chọn độ phân giải màn hình:"
echo "  1) 1920x1080 @ 60Hz (Full HD) - Khuyến nghị"
echo "  2) 1280x720 @ 60Hz (HD)"
echo "  3) 1024x768 @ 60Hz (XGA)"
echo "  4) 800x480 @ 60Hz (Màn hình 7 inch)"
echo "  5) Auto (tự nhận dạng từ monitor)"
echo
read -p "Chọn (1-5, mặc định 1): " choice

case "$choice" in
    2)
        HDMI_GROUP=2
        HDMI_MODE=85
        RESOLUTION="1280x720 @ 60Hz"
        ;;
    3)
        HDMI_GROUP=2
        HDMI_MODE=16
        RESOLUTION="1024x768 @ 60Hz"
        ;;
    4)
        HDMI_GROUP=2
        HDMI_MODE=87
        HDMI_CVT="800 480 60 6 0 0 0"
        RESOLUTION="800x480 @ 60Hz (custom)"
        ;;
    5)
        HDMI_GROUP=0
        HDMI_MODE=0
        RESOLUTION="Auto detect"
        ;;
    *)
        HDMI_GROUP=2
        HDMI_MODE=82
        RESOLUTION="1920x1080 @ 60Hz"
        ;;
esac

echo
echo -e "${GREEN}📺 Cấu hình: $RESOLUTION${NC}"

# Thêm cấu hình HDMI
cat << EOF >> "$CONFIG_FILE"

# ============================================
# Smart C AI - HDMI Configuration
# Configured: $(date)
# Resolution: $RESOLUTION
# ============================================
hdmi_force_hotplug=1
hdmi_group=$HDMI_GROUP
hdmi_mode=$HDMI_MODE
hdmi_drive=2
disable_overscan=1
EOF

# Thêm CVT cho màn hình 7 inch
if [ -n "$HDMI_CVT" ]; then
    echo "hdmi_cvt=$HDMI_CVT" >> "$CONFIG_FILE"
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          ✅ DISPLAY ĐÃ CẤU HÌNH!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "📍 Độ phân giải: ${YELLOW}$RESOLUTION${NC}"
echo -e "📍 Config file: $CONFIG_FILE"
echo
echo -e "${YELLOW}⚠️  Cần REBOOT để áp dụng:${NC}"
echo "   sudo reboot"
echo

# Hỏi reboot
read -p "Reboot ngay? (y/n): " reboot_choice
if [[ "$reboot_choice" =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    reboot
fi
