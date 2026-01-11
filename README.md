# 💻 Bizino AI DEV - VS Code + Copilot Kit

> Software Company Agent System Kit for **VS Code** with **GitHub Copilot**

## 📦 Quick Install

```bash
# From this directory
./install.sh [target_project_directory]

# Or from root
../install.sh --vscode [target_project_directory]
```

## 📁 What Gets Installed

```
your-project/
├── .github/
│   ├── copilot-instructions.md  # Main Copilot configuration
│   ├── prompts/                 # Reusable prompt templates
│   │   ├── cook.prompt.md       # 🔥 Full auto pipeline
│   │   ├── plan.prompt.md       # Create PRD
│   │   ├── design.prompt.md     # System design
│   │   ├── code.prompt.md       # Implementation
│   │   ├── test.prompt.md       # Testing
│   │   ├── review.prompt.md     # Code review
│   │   ├── fix.prompt.md        # Bug fixing
│   │   ├── git.prompt.md        # Git operations
│   │   └── init.prompt.md       # Project initialization
│   ├── roles/                   # AI role definitions
│   │   ├── product-manager.md
│   │   ├── architect.md
│   │   ├── engineer.md
│   │   ├── qa-engineer.md
│   │   ├── code-reviewer.md
│   │   ├── researcher.md
│   │   └── devops.md
│   ├── README.md
│   └── GETTING_STARTED.md
├── plans/                       # Project documentation
│   ├── active/
│   ├── reports/
│   └── archive/
└── docs/
    └── templates/
```

## ⚙️ Setup

### 1. Enable Custom Instructions

1. Open VS Code Settings (`Cmd+,` or `Ctrl+,`)
2. Search for `github.copilot.chat.codeGeneration.useInstructionFiles`
3. Set to `true`

### 2. Verify Installation

The `.github/copilot-instructions.md` file will be automatically loaded by Copilot Chat.

## 🚀 Usage

### Using Prompt Files in Copilot Chat

Reference prompt files using `#file:` syntax:

```
@workspace #file:.github/prompts/cook.prompt.md Build an e-commerce app with user auth
```

| Prompt File | Description |
|-------------|-------------|
| `cook.prompt.md` | 🔥 Full auto pipeline - from idea to MVP |
| `plan.prompt.md` | Create PRD for a feature |
| `design.prompt.md` | Create system design from PRD |
| `code.prompt.md` | Implement code from design |
| `test.prompt.md` | Run tests and generate reports |
| `review.prompt.md` | Code review and quality check |
| `fix.prompt.md` | Debug and fix issues |
| `git.prompt.md` | Git operations (commit, push, PR) |

### Example Commands

```
# Full development pipeline
@workspace #file:.github/prompts/cook.prompt.md Build a todo app with tags and priorities

# Plan a feature
@workspace #file:.github/prompts/plan.prompt.md User authentication with social login

# Fix a bug
@workspace #file:.github/prompts/fix.prompt.md The form validation is not working

# Code review
@workspace #file:.github/prompts/review.prompt.md Review the authentication module
```

### Using Roles

You can also reference role files for persona-based responses:

```
@workspace #file:.github/roles/architect.md Design the database schema for user management
```

## 🎭 Roles

The kit includes 7 specialized AI roles:

1. **Product Manager** - Requirements analysis, PRD creation
2. **Architect** - System design, technical decisions
3. **Engineer** - Code implementation
4. **QA Engineer** - Testing, quality assurance
5. **Code Reviewer** - Code review, best practices
6. **Researcher** - Technical research, documentation
7. **DevOps** - Deployment, infrastructure

## 📝 Custom Instructions

The `copilot-instructions.md` file contains:
- System identity and behavior rules
- Code generation preferences
- Output format specifications
- Project-specific conventions

Edit this file to customize Copilot's behavior for your project.

## 📚 Documentation

- [GETTING_STARTED.md](./GETTING_STARTED.md) - Quick start guide
- [prompts/](./prompts/) - All available prompt templates
- [roles/](./roles/) - Role specifications

---

**Bizino AI DEV** - *Transforming Ideas into Software Automatically*
