#!/bin/bash
# =============================================================================
#            SMART C AI - INSTALL DEPENDENCIES
# =============================================================================
# Cài đặt tất cả Python dependencies cần thiết
# Chạy: bash scripts/install_deps.sh
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

APP_HOME="$HOME/.digits"
if [ ! -d "$APP_HOME" ]; then
    APP_HOME="$HOME/.xiaozhi"
fi

echo -e "${GREEN}🔧 Cài đặt Python dependencies cho Smart C AI...${NC}"
echo "📁 App directory: $APP_HOME"
echo ""

cd "$APP_HOME" || exit 1

# Kiểm tra requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Không tìm thấy requirements.txt${NC}"
    exit 1
fi

# Cài đặt với pip
echo -e "${YELLOW}Đang cài đặt packages...${NC}"
echo ""

# Thử với --break-system-packages (Pi OS mới)
pip3 install --user --break-system-packages -r requirements.txt 2>/dev/null || \
pip3 install --user -r requirements.txt 2>/dev/null || \
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Cài đặt dependencies hoàn tất!${NC}"
    echo ""
    echo "Chạy app: ~/.digits/run.sh"
else
    echo ""
    echo -e "${RED}❌ Có lỗi khi cài đặt. Thử chạy thủ công:${NC}"
    echo "   pip3 install --user colorlog aiohttp websockets numpy sounddevice"
fi
