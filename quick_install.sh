#!/bin/bash
# Quick installer - Cài đặt app với icon trên desktop (không cần build)

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          🎯 Xiaozhi AI Quick Installer                       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo

INSTALL_DIR="$HOME/.digits"
DESKTOP_FILE="$HOME/.local/share/applications/xiaozhi.desktop"
DESKTOP_SHORTCUT="$HOME/Desktop/xiaozhi.desktop"

echo -e "${YELLOW}→ Cài đặt dependencies...${NC}"
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || \
pip3 install -r requirements.txt --user 2>/dev/null || \
echo -e "${YELLOW}⚠️  Bỏ qua pip install (có thể đã cài)${NC}"

echo -e "${YELLOW}→ Tạo thư mục cài đặt...${NC}"
mkdir -p "$INSTALL_DIR"

echo -e "${YELLOW}→ Copy files...${NC}"
rsync -av \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='build' \
  --exclude='dist' \
  --exclude='logs' \
  ./ "$INSTALL_DIR/"

echo -e "${YELLOW}→ Tạo launcher script...${NC}"
cat > "$INSTALL_DIR/xiaozhi_launcher.sh" << 'EOF'
#!/bin/bash
cd "$HOME/.digits"
python3 main.py --mode gui "$@" 2>&1 | tee -a logs/xiaozhi.log
EOF
chmod +x "$INSTALL_DIR/xiaozhi_launcher.sh"

echo -e "${YELLOW}→ Tạo desktop icons...${NC}"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/Desktop"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Xiaozhi AI
GenericName=Voice Assistant
Comment=Voice AI Assistant for Raspberry Pi with TV Display
Exec=$INSTALL_DIR/xiaozhi_launcher.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
Categories=Audio;AudioVideo;Utility;
StartupNotify=true
Keywords=voice;ai;assistant;xiaozhi;
EOF

cp "$DESKTOP_FILE" "$DESKTOP_SHORTCUT"
chmod +x "$DESKTOP_FILE"
chmod +x "$DESKTOP_SHORTCUT"

# Trust desktop file
if command -v gio &> /dev/null; then
    gio set "$DESKTOP_SHORTCUT" metadata::trusted true 2>/dev/null || true
fi

# Create symbolic link
echo -e "${YELLOW}→ Tạo symbolic link...${NC}"
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/xiaozhi_launcher.sh" "$HOME/.local/bin/xiaozhi" 2>/dev/null || true

# Add to PATH if not already
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

echo
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║               ✅ Cài đặt hoàn tất!                            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${BLUE}📍 Vị trí cài đặt:${NC} $INSTALL_DIR"
echo -e "${BLUE}🖥️  Desktop icon:${NC} ~/Desktop/xiaozhi.desktop"
echo -e "${BLUE}📱 Menu entry:${NC} Applications → Xiaozhi AI"
echo
echo -e "${GREEN}Cách chạy:${NC}"
echo -e "  1. ${YELLOW}Double-click icon trên Desktop${NC}"
echo -e "  2. Tìm 'Xiaozhi AI' trong menu ứng dụng"
echo -e "  3. Terminal: ${YELLOW}xiaozhi${NC} (sau khi logout/login lại)"
echo
echo -e "${BLUE}📁 Logs:${NC} $INSTALL_DIR/logs/xiaozhi.log"
echo -e "${BLUE}⚙️  Config:${NC} $INSTALL_DIR/config/config.json"
echo
echo -e "${YELLOW}Gỡ cài đặt:${NC} rm -rf $INSTALL_DIR ~/.local/share/applications/xiaozhi.desktop ~/Desktop/xiaozhi.desktop ~/.local/bin/xiaozhi"
echo
