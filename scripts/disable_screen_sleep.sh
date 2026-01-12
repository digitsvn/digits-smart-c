#!/bin/bash
# =============================================================================
#            SMART C AI - DISABLE SCREEN SLEEP
# =============================================================================
# Ngăn màn hình ngủ khi app đang chạy
# Chạy: bash scripts/disable_screen_sleep.sh
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🖥️  Đang tắt chế độ ngủ màn hình...${NC}"

# =====================================================
# 1. Tắt screen blanking trên X11
# =====================================================
if [ -n "$DISPLAY" ]; then
    xset s off 2>/dev/null || true
    xset -dpms 2>/dev/null || true
    xset s noblank 2>/dev/null || true
    echo "   ✓ X11 screen blanking disabled"
fi

# =====================================================
# 2. Tắt dpms trong lightdm
# =====================================================
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"
if [ -f "$LIGHTDM_CONF" ]; then
    if ! grep -q "xserver-command=X -s 0 -dpms" "$LIGHTDM_CONF" 2>/dev/null; then
        sudo sed -i '/^\[Seat:\*\]/a xserver-command=X -s 0 -dpms' "$LIGHTDM_CONF" 2>/dev/null || true
        echo "   ✓ LightDM dpms disabled"
    fi
fi

# =====================================================
# 3. Thêm vào autostart script
# =====================================================
AUTOSTART="$HOME/.config/labwc/autostart"
if [ -f "$AUTOSTART" ]; then
    if ! grep -q "xset" "$AUTOSTART" 2>/dev/null; then
        echo "xset s off -dpms 2>/dev/null || true" >> "$AUTOSTART"
        echo "   ✓ Added to labwc autostart"
    fi
fi

# =====================================================
# 4. Tạo systemd service để chống sleep
# =====================================================
sudo tee /etc/systemd/system/disable-screen-blank.service > /dev/null << 'EOF'
[Unit]
Description=Disable Screen Blanking
After=graphical.target

[Service]
Type=oneshot
Environment=DISPLAY=:0
ExecStart=/usr/bin/xset s off -dpms
RemainAfterExit=yes

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable disable-screen-blank.service 2>/dev/null || true
echo "   ✓ Systemd service created"

# =====================================================
# 5. Thêm vào boot config (Pi specific)
# =====================================================
CONFIG_FILE=""
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f /boot/config.txt ]; then
    CONFIG_FILE="/boot/config.txt"
fi

if [ -n "$CONFIG_FILE" ]; then
    if ! grep -q "hdmi_blanking=0" "$CONFIG_FILE" 2>/dev/null; then
        echo "" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "# Disable HDMI blanking" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "hdmi_blanking=0" | sudo tee -a "$CONFIG_FILE" > /dev/null
        echo "   ✓ HDMI blanking disabled in config.txt"
    fi
fi

# =====================================================
# 6. Tắt console blanking
# =====================================================
sudo bash -c 'echo -ne "\033[9;0]" > /dev/tty1' 2>/dev/null || true
if ! grep -q "consoleblank=0" /boot/firmware/cmdline.txt 2>/dev/null && \
   ! grep -q "consoleblank=0" /boot/cmdline.txt 2>/dev/null; then
    if [ -f /boot/firmware/cmdline.txt ]; then
        sudo sed -i 's/$/ consoleblank=0/' /boot/firmware/cmdline.txt
    elif [ -f /boot/cmdline.txt ]; then
        sudo sed -i 's/$/ consoleblank=0/' /boot/cmdline.txt
    fi
    echo "   ✓ Console blanking disabled"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     ✅ MÀN HÌNH SẼ KHÔNG TỰ ĐỘNG TẮT!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Reboot để áp dụng: sudo reboot${NC}"
