#!/bin/bash
# =============================================================================
# Smart C AI - Build Package Script
# =============================================================================
# Tạo package cài đặt cho Raspberry Pi
# 
# Chạy: ./build_package.sh [version]
# Ví dụ: ./build_package.sh 1.0.0
# =============================================================================

set -e

# Màu sắc
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Thông tin package
APP_NAME="smartc"
APP_DISPLAY_NAME="Smart C AI"
VERSION="${1:-1.0.0}"
ARCH="armhf"  # arm64 cho Pi 4 64-bit
MAINTAINER="Smart C Team <support@xiaozhi-ai-iot.vn>"
DESCRIPTION="Trợ lý AI thông minh cho Raspberry Pi"

# Thư mục làm việc
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
PACKAGE_NAME="${APP_NAME}_${VERSION}_${ARCH}"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           Smart C AI - Build Package v${VERSION}                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Dọn dẹp
echo -e "${YELLOW}→ Dọn dẹp thư mục build cũ...${NC}"
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# =============================================================================
# 1. Tạo tarball installer
# =============================================================================
echo -e "${YELLOW}→ Tạo tarball installer...${NC}"

TARBALL_DIR="$BUILD_DIR/tarball/${APP_NAME}-${VERSION}"
mkdir -p "$TARBALL_DIR"

# Copy source code (loại bỏ các file không cần thiết)
rsync -av \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='build' \
    --exclude='dist' \
    --exclude='logs/*.log' \
    --exclude='.vscode' \
    --exclude='*.egg-info' \
    --exclude='.pytest_cache' \
    --exclude='venv' \
    --exclude='*.sw?' \
    "$SCRIPT_DIR/" "$TARBALL_DIR/"

# Tạo installer script trong package
cat > "$TARBALL_DIR/install.sh" << 'INSTALLER_EOF'
#!/bin/bash
# Smart C AI - One-click Installer
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              🤖 Smart C AI - Installer                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Kiểm tra quyền root cho một số tác vụ
SUDO=""
if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
    echo -e "${YELLOW}Một số bước cần quyền sudo...${NC}"
fi

INSTALL_DIR="$HOME/.digits"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}→ Bước 1: Cài đặt system dependencies...${NC}"
$SUDO apt-get update -y
$SUDO apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    python3-pyqt5 python3-pyqt5.qtquick \
    libportaudio2 portaudio19-dev libsndfile1 \
    alsa-utils pulseaudio \
    network-manager \
    libopus0 libopus-dev

echo -e "${YELLOW}→ Bước 2: Copy files vào $INSTALL_DIR...${NC}"
mkdir -p "$INSTALL_DIR"
rsync -av --delete \
    --exclude='install.sh' \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"

echo -e "${YELLOW}→ Bước 3: Cài đặt Python dependencies...${NC}"
pip3 install --user -r "$INSTALL_DIR/requirements.txt" || \
pip3 install --user sounddevice numpy aiohttp websockets qasync sherpa-onnx

echo -e "${YELLOW}→ Bước 4: Cấu hình audio...${NC}"
# Thêm user vào group audio
$SUDO usermod -aG audio $USER 2>/dev/null || true

# Thiết lập âm lượng
amixer set Master 80% unmute 2>/dev/null || true
amixer set PCM 80% unmute 2>/dev/null || true

echo -e "${YELLOW}→ Bước 5: Tạo launcher và desktop entry...${NC}"

# Tạo launcher script
cat > "$INSTALL_DIR/run.sh" << 'EOF'
#!/bin/bash
cd "$HOME/.digits"
mkdir -p logs
exec python3 main.py --mode gui "$@" 2>&1 | tee -a logs/smartc.log
EOF
chmod +x "$INSTALL_DIR/run.sh"

# Tạo desktop entry
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/Desktop"

cat > "$HOME/.local/share/applications/smartc.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Smart C AI
GenericName=Trợ lý AI
Comment=Trợ lý AI thông minh cho Raspberry Pi
Exec=$INSTALL_DIR/run.sh
Icon=$INSTALL_DIR/assets/icon.png
Terminal=false
Categories=Audio;AudioVideo;Utility;
StartupNotify=true
Keywords=voice;ai;assistant;smartc;
EOF

# Copy desktop shortcut
cp "$HOME/.local/share/applications/smartc.desktop" "$HOME/Desktop/" 2>/dev/null || true
chmod +x "$HOME/Desktop/smartc.desktop" 2>/dev/null || true

# Trust desktop file nếu có gio
if command -v gio &> /dev/null; then
    gio set "$HOME/Desktop/smartc.desktop" metadata::trusted true 2>/dev/null || true
fi

# Tạo symlink để chạy từ terminal
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/run.sh" "$HOME/.local/bin/smartc"

echo -e "${YELLOW}→ Bước 6: Thiết lập autostart (optional)...${NC}"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/smartc.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Smart C AI
Exec=$INSTALL_DIR/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Start Smart C AI on login
EOF

echo
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo -e "║               ✅ CÀI ĐẶT HOÀN TẤT!                             ║"
echo -e "╚═══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${BLUE}📍 Vị trí cài đặt:${NC} $INSTALL_DIR"
echo -e "${BLUE}🖥️  Desktop:${NC} Double-click icon Smart C AI trên Desktop"
echo -e "${BLUE}💻 Terminal:${NC} smartc (sau khi logout/login)"
echo
echo -e "${YELLOW}Lần đầu chạy:${NC}"
echo "  1. Kết nối WiFi (nếu chưa có)"
echo "  2. Cấu hình MIC/Loa trong Settings"
echo "  3. Kích hoạt thiết bị với server"
echo
echo -e "${GREEN}Khởi động ngay:${NC} $INSTALL_DIR/run.sh"
echo
INSTALLER_EOF

chmod +x "$TARBALL_DIR/install.sh"

# Tạo uninstall script
cat > "$TARBALL_DIR/uninstall.sh" << 'UNINSTALLER_EOF'
#!/bin/bash
# Smart C AI - Uninstaller
set -e

echo "🗑️  Gỡ cài đặt Smart C AI..."

INSTALL_DIR="$HOME/.digits"

# Xóa files
rm -rf "$INSTALL_DIR"
rm -f "$HOME/.local/share/applications/smartc.desktop"
rm -f "$HOME/Desktop/smartc.desktop"
rm -f "$HOME/.config/autostart/smartc.desktop"
rm -f "$HOME/.local/bin/smartc"

echo "✅ Đã gỡ cài đặt Smart C AI"
UNINSTALLER_EOF

chmod +x "$TARBALL_DIR/uninstall.sh"

# Tạo tarball
cd "$BUILD_DIR/tarball"
tar -czvf "$DIST_DIR/${APP_NAME}-${VERSION}.tar.gz" "${APP_NAME}-${VERSION}"

echo -e "${GREEN}✓ Tarball: $DIST_DIR/${APP_NAME}-${VERSION}.tar.gz${NC}"

# =============================================================================
# 2. Tạo .deb package
# =============================================================================
echo -e "${YELLOW}→ Tạo .deb package...${NC}"

DEB_DIR="$BUILD_DIR/deb/$PACKAGE_NAME"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/opt/smartc"
mkdir -p "$DEB_DIR/usr/share/applications"
mkdir -p "$DEB_DIR/usr/local/bin"

# Copy source vào /opt/smartc
rsync -av \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='build' \
    --exclude='dist' \
    --exclude='logs/*.log' \
    --exclude='.vscode' \
    --exclude='*.egg-info' \
    "$SCRIPT_DIR/" "$DEB_DIR/opt/smartc/"

# Tạo control file
cat > "$DEB_DIR/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $VERSION
Section: misc
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pip, python3-pyqt5, libportaudio2, alsa-utils, network-manager
Maintainer: $MAINTAINER
Description: $DESCRIPTION
 Smart C AI là trợ lý AI thông minh với các tính năng:
 - Nhận diện giọng nói qua wake word
 - Kết nối WiFi tự động qua hotspot
 - Hỗ trợ MIC và Loa
 - Giao diện GUI đẹp
Homepage: https://xiaozhi-ai-iot.vn
EOF

# Tạo postinst script
cat > "$DEB_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

echo "→ Cài đặt Python dependencies..."
pip3 install --user sounddevice numpy aiohttp websockets qasync || true

# Tạo symlink
ln -sf /opt/smartc/run.sh /usr/local/bin/smartc

# Cấu hình audio
usermod -aG audio $SUDO_USER 2>/dev/null || true

echo "✅ Smart C AI đã được cài đặt!"
echo "Chạy: smartc hoặc tìm trong Applications menu"
EOF
chmod 755 "$DEB_DIR/DEBIAN/postinst"

# Tạo postrm script
cat > "$DEB_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

rm -f /usr/local/bin/smartc
rm -rf /opt/smartc
echo "Smart C AI đã được gỡ cài đặt"
EOF
chmod 755 "$DEB_DIR/DEBIAN/postrm"

# Tạo launcher trong package
cat > "$DEB_DIR/opt/smartc/run.sh" << 'EOF'
#!/bin/bash
cd /opt/smartc
mkdir -p "$HOME/.digits/logs" "$HOME/.digits/config"

# Copy config nếu chưa có
if [ ! -f "$HOME/.digits/config/config.json" ]; then
    cp /opt/smartc/config/config.json "$HOME/.digits/config/" 2>/dev/null || true
fi

exec python3 main.py --mode gui "$@" 2>&1 | tee -a "$HOME/.digits/logs/smartc.log"
EOF
chmod +x "$DEB_DIR/opt/smartc/run.sh"

# Tạo desktop entry
cat > "$DEB_DIR/usr/share/applications/smartc.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Smart C AI
GenericName=Trợ lý AI
Comment=Trợ lý AI thông minh cho Raspberry Pi
Exec=/opt/smartc/run.sh
Icon=/opt/smartc/assets/icon.png
Terminal=false
Categories=Audio;AudioVideo;Utility;
StartupNotify=true
Keywords=voice;ai;assistant;smartc;
EOF

# Build .deb
dpkg-deb --build "$DEB_DIR" "$DIST_DIR/${PACKAGE_NAME}.deb" 2>/dev/null || \
    echo -e "${YELLOW}⚠️  dpkg-deb không có sẵn, bỏ qua .deb${NC}"

if [ -f "$DIST_DIR/${PACKAGE_NAME}.deb" ]; then
    echo -e "${GREEN}✓ DEB package: $DIST_DIR/${PACKAGE_NAME}.deb${NC}"
fi

# =============================================================================
# 3. Tạo one-line installer script
# =============================================================================
echo -e "${YELLOW}→ Tạo one-line installer script...${NC}"

cat > "$DIST_DIR/install_online.sh" << 'ONLINE_EOF'
#!/bin/bash
# Smart C AI - Online Installer
# Chạy: curl -sSL https://your-server.com/install.sh | bash

set -e

DOWNLOAD_URL="https://github.com/user/smartc/releases/latest/download/smartc-latest.tar.gz"
TEMP_DIR=$(mktemp -d)

echo "🤖 Đang tải Smart C AI..."
cd "$TEMP_DIR"
curl -sSL "$DOWNLOAD_URL" -o smartc.tar.gz
tar -xzf smartc.tar.gz
cd smartc-*

echo "📦 Đang cài đặt..."
bash install.sh

# Cleanup
rm -rf "$TEMP_DIR"
echo "✅ Hoàn tất!"
ONLINE_EOF

chmod +x "$DIST_DIR/install_online.sh"

# =============================================================================
# Tổng kết
# =============================================================================
echo
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo -e "║                    BUILD HOÀN TẤT!                             ║"
echo -e "╚═══════════════════════════════════════════════════════════════╝${NC}"
echo
echo -e "${CYAN}📦 Packages đã tạo:${NC}"
echo
ls -lh "$DIST_DIR/"
echo
echo -e "${BLUE}Cách sử dụng:${NC}"
echo
echo -e "${YELLOW}1. Tarball (khuyến nghị):${NC}"
echo "   - Copy ${APP_NAME}-${VERSION}.tar.gz tới Raspberry Pi"
echo "   - Giải nén: tar -xzf ${APP_NAME}-${VERSION}.tar.gz"
echo "   - Cài đặt: cd ${APP_NAME}-${VERSION} && bash install.sh"
echo
if [ -f "$DIST_DIR/${PACKAGE_NAME}.deb" ]; then
echo -e "${YELLOW}2. DEB package:${NC}"
echo "   - Copy ${PACKAGE_NAME}.deb tới Raspberry Pi"
echo "   - Cài đặt: sudo dpkg -i ${PACKAGE_NAME}.deb"
echo "   - Fix dependencies: sudo apt-get install -f"
echo
fi
echo -e "${YELLOW}3. Online installer:${NC}"
echo "   - Upload packages lên server"
echo "   - curl -sSL https://your-server.com/install.sh | bash"
echo
