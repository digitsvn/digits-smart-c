#!/bin/bash
# =============================================================================
#                    SMART C AI - PACKAGE BUILDER
# =============================================================================
# Script này tạo các gói cài đặt khác nhau:
# 1. .tar.gz - Archive chứa toàn bộ source + setup.sh
# 2. Self-extracting installer (.run) - Chạy 1 lần để cài
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Config
VERSION="${1:-1.0.0}"
APP_NAME="smartc"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SOURCE_DIR/build/package"
OUTPUT_DIR="$SOURCE_DIR/dist"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           SMART C AI - PACKAGE BUILDER v$VERSION                     ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Clean previous builds
echo -e "${YELLOW}[1/5] Dọn dẹp build cũ...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"

# Copy source files
echo -e "${YELLOW}[2/5] Copy source files...${NC}"
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
    --exclude='logs/*.log' \
    --exclude='cache/*' \
    "$SOURCE_DIR/" "$BUILD_DIR/$APP_NAME/"

# Clean up logs and cache in package
rm -rf "$BUILD_DIR/$APP_NAME/logs"/*
rm -rf "$BUILD_DIR/$APP_NAME/cache"/*
mkdir -p "$BUILD_DIR/$APP_NAME/logs"
mkdir -p "$BUILD_DIR/$APP_NAME/cache"
touch "$BUILD_DIR/$APP_NAME/logs/.gitkeep"
touch "$BUILD_DIR/$APP_NAME/cache/.gitkeep"

# Create tarball
echo -e "${YELLOW}[3/5] Tạo tarball...${NC}"
cd "$BUILD_DIR"
tar -czvf "$OUTPUT_DIR/${APP_NAME}-${VERSION}.tar.gz" "$APP_NAME"

# Create self-extracting installer
echo -e "${YELLOW}[4/5] Tạo self-extracting installer (.run)...${NC}"

# Create installer header script
cat > "$OUTPUT_DIR/${APP_NAME}-${VERSION}-installer.run" << 'INSTALLER_HEADER'
#!/bin/bash
# =============================================================================
#            SMART C AI - SELF-EXTRACTING INSTALLER
# =============================================================================

EXTRACT_DIR=$(mktemp -d)
SCRIPT_SIZE=SCRIPT_SIZE_PLACEHOLDER

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         🤖 SMART C AI INSTALLER                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo
echo "Đang giải nén..."

# Extract tarball from this script
tail -n +$SCRIPT_SIZE "$0" | tar -xzf - -C "$EXTRACT_DIR"

if [ $? -ne 0 ]; then
    echo "Lỗi giải nén!"
    rm -rf "$EXTRACT_DIR"
    exit 1
fi

echo "Đang cài đặt..."
cd "$EXTRACT_DIR/smartc"
bash setup.sh

# Clean up
rm -rf "$EXTRACT_DIR"
exit 0

# === TARBALL DATA BELOW ===
INSTALLER_HEADER

# Calculate line count of header
HEADER_LINES=$(($(wc -l < "$OUTPUT_DIR/${APP_NAME}-${VERSION}-installer.run") + 1))

# Replace placeholder
sed -i "s/SCRIPT_SIZE_PLACEHOLDER/$HEADER_LINES/" "$OUTPUT_DIR/${APP_NAME}-${VERSION}-installer.run"

# Append tarball
cat "$OUTPUT_DIR/${APP_NAME}-${VERSION}.tar.gz" >> "$OUTPUT_DIR/${APP_NAME}-${VERSION}-installer.run"

# Make executable
chmod +x "$OUTPUT_DIR/${APP_NAME}-${VERSION}-installer.run"

# Summary
echo -e "${YELLOW}[5/5] Hoàn tất!${NC}"
echo
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    📦 PACKAGES CREATED                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo

ls -lh "$OUTPUT_DIR/"

echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📋 HƯỚNG DẪN SỬ DỤNG:${NC}"
echo
echo -e "${YELLOW}Cách 1: Tarball${NC}"
echo -e "   1. Copy file: ${GREEN}$OUTPUT_DIR/${APP_NAME}-${VERSION}.tar.gz${NC}"
echo -e "   2. Giải nén:  ${GREEN}tar -xzf ${APP_NAME}-${VERSION}.tar.gz${NC}"
echo -e "   3. Cài đặt:   ${GREEN}cd ${APP_NAME} && bash setup.sh${NC}"
echo
echo -e "${YELLOW}Cách 2: Self-Extracting Installer (Đơn giản nhất)${NC}"
echo -e "   1. Copy file: ${GREEN}$OUTPUT_DIR/${APP_NAME}-${VERSION}-installer.run${NC}"
echo -e "   2. Chạy:      ${GREEN}bash ${APP_NAME}-${VERSION}-installer.run${NC}"
echo
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Clean build dir
rm -rf "$BUILD_DIR"

echo -e "${GREEN}✓ Build hoàn tất!${NC}"
