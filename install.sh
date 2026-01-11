#!/bin/bash

# ==============================================================================
# 🚀 BIZINO AI DEV - VS Code + Copilot Kit
# ==============================================================================
# Installation Script for VS Code with GitHub Copilot
# Version: 2.1.0
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║   💻 BIZINO AI DEV - VS Code + Copilot Kit                        ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Target Directory (default: parent directory - project root)
TARGET_DIR="${1:-..}"
TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd || echo "$TARGET_DIR")"

# Create target if not exists
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}Creating target directory: $TARGET_DIR${NC}"
    mkdir -p "$TARGET_DIR"
fi

echo -e "${BLUE}Installing VS Code + Copilot Kit to: ${WHITE}$TARGET_DIR${NC}"
echo ""

# Create .github directory structure
mkdir -p "$TARGET_DIR/.github/prompts"
mkdir -p "$TARGET_DIR/.github/roles"

# Copy copilot-instructions.md
if [ -f "$SCRIPT_DIR/copilot-instructions.md" ]; then
    cp "$SCRIPT_DIR/copilot-instructions.md" "$TARGET_DIR/.github/"
    echo -e "${GREEN}  ✓ copilot-instructions.md copied${NC}"
fi

# Copy prompts
if [ -d "$SCRIPT_DIR/prompts" ]; then
    cp -r "$SCRIPT_DIR/prompts/"*.md "$TARGET_DIR/.github/prompts/" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Prompts copied${NC}"
fi

# Copy roles
if [ -d "$SCRIPT_DIR/roles" ]; then
    cp -r "$SCRIPT_DIR/roles/"*.md "$TARGET_DIR/.github/roles/" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Roles copied${NC}"
fi

# Copy docs
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$TARGET_DIR/.github/"
[ -f "$SCRIPT_DIR/GETTING_STARTED.md" ] && cp "$SCRIPT_DIR/GETTING_STARTED.md" "$TARGET_DIR/.github/"

# Copy skills directory
if [ -d "$SCRIPT_DIR/skills" ]; then
    cp -r "$SCRIPT_DIR/skills" "$TARGET_DIR/.github/"
    echo -e "${GREEN}  ✓ Skills copied${NC}"
fi

# Copy docs directory
if [ -d "$SCRIPT_DIR/docs" ]; then
    cp -r "$SCRIPT_DIR/docs" "$TARGET_DIR/"
    echo -e "${GREEN}  ✓ docs/ copied${NC}"
fi

# Copy guide directory
if [ -d "$SCRIPT_DIR/guide" ]; then
    cp -r "$SCRIPT_DIR/guide" "$TARGET_DIR/"
    echo -e "${GREEN}  ✓ guide/ copied${NC}"
fi

# Create common directories
mkdir -p "$TARGET_DIR/plans/active"
mkdir -p "$TARGET_DIR/plans/reports"
mkdir -p "$TARGET_DIR/plans/archive"
mkdir -p "$TARGET_DIR/docs/templates"

# Copy templates
if [ -d "$SCRIPT_DIR/templates/plans" ]; then
    cp -r "$SCRIPT_DIR/templates/plans/"* "$TARGET_DIR/plans/" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Plan templates copied${NC}"
fi

if [ -d "$SCRIPT_DIR/templates/docs" ]; then
    cp -r "$SCRIPT_DIR/templates/docs/"* "$TARGET_DIR/docs/templates/" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Doc templates copied${NC}"
fi

touch "$TARGET_DIR/plans/active/.gitkeep"
touch "$TARGET_DIR/plans/reports/.gitkeep"
touch "$TARGET_DIR/plans/archive/.gitkeep"

echo -e "${GREEN}  ✓ Project structure created${NC}"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      ✅ VS CODE + COPILOT KIT INSTALLED!                          ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}💻 Setup Instructions:${NC}"
echo ""
echo -e "  ${WHITE}1. Enable Custom Instructions in VS Code:${NC}"
echo -e "     Settings → Search 'github.copilot.chat.codeGeneration.useInstructionFiles'"
echo -e "     Set to: ${GREEN}true${NC}"
echo ""
echo -e "  ${WHITE}2. Use in Copilot Chat:${NC}"
echo ""
echo -e "    ${GREEN}@workspace #file:.github/prompts/cook.prompt.md${NC} Build an e-commerce app"
echo -e "    ${GREEN}@workspace #file:.github/prompts/plan.prompt.md${NC} User authentication"
echo -e "    ${GREEN}@workspace #file:.github/prompts/code.prompt.md${NC} Implement the design"
echo -e "    ${GREEN}@workspace #file:.github/prompts/fix.prompt.md${NC} Debug the login error"
echo ""
echo -e "${WHITE}📁 Installed to: ${GREEN}$TARGET_DIR${NC}"
echo ""
