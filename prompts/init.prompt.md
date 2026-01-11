# /init - Initialize Bizino AI DEV

> **Good initialization = smooth development**

## 🎯 Purpose
Set up Bizino AI DEV for a new or existing project.

## Steps

### 1. Detect Project Type
[AUTO] Analyze project:

```bash
# Check for existing frameworks
ls package.json 2>/dev/null && echo "Node.js project detected"
ls composer.json 2>/dev/null && echo "PHP/Laravel project detected"
ls requirements.txt 2>/dev/null && echo "Python project detected"
ls go.mod 2>/dev/null && echo "Go project detected"
```

### 2. Create Directory Structure
[AUTO] Create required directories:

```bash
mkdir -p plans/active
mkdir -p plans/reports
mkdir -p plans/archive
mkdir -p docs/templates
```

### 3. Copy Copilot Kit to .github

```bash
# Copy prompt files
mkdir -p .github/prompts
cp -r .github/prompts/* .github/prompts/

# Copy instructions
cp .github/copilot-instructions.md .github/copilot-instructions.md
```

### 4. Create Project Configuration

Create `.github/project.json`:
```json
{
  "name": "{project_name}",
  "type": "{node/php/python/go}",
  "version": "1.0.0",
  "ai_dev": {
    "auto_commit": true,
    "auto_deploy": false,
    "test_coverage_min": 80,
    "code_review_strict": true
  },
  "ui_framework": "{semi-design/existing}",
  "created_at": "{date}"
}
```

### 5. Create .gitignore additions

Append to `.gitignore`:
```
# Bizino AI DEV
plans/active/*
!plans/active/.gitkeep
.env.local
*.log
```

### 6. Verify Setup

```bash
echo "✅ Bizino AI DEV initialized successfully!"
echo ""
echo "📁 Project Structure:"
echo "├── .github/"
echo "│   ├── copilot-instructions.md"
echo "│   ├── prompts/"
echo "│   └── project.json"
echo "├── plans/"
echo "│   ├── active/"
echo "│   ├── reports/"
echo "│   └── archive/"
echo "└── docs/"
echo "    └── templates/"
echo ""
echo "🚀 Ready to use! Try: @workspace /cook Build a [your feature]"
```

---

## Quick Start Commands

After initialization, you can use:

| Command | Description |
|---------|-------------|
| `@workspace /cook [request]` | Full auto pipeline |
| `@workspace /plan [feature]` | Create PRD |
| `@workspace /design [feature]` | System design |
| `@workspace /code [feature]` | Implement |
| `@workspace /test` | Run tests |
| `@workspace /review` | Code review |
| `@workspace /fix [bug]` | Debug |
| `@workspace /git` | Git workflow |

---

## Example Usage

```
@workspace /init Set up Bizino AI DEV for this React project

@workspace /init Initialize agent system for Laravel backend
```
