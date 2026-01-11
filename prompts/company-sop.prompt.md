---
description: SOP Công Ty Phần Mềm AI - Quy trình chuẩn từ yêu cầu đến sản phẩm hoàn chỉnh
---

# 🏢 Bizino AI DEV - Standard Operating Procedure

> **Triết lý**: "Code = SOP(Team)" - Mỗi agent đóng vai trò chuyên biệt, giao tiếp qua output có cấu trúc, tuân theo workflow chuẩn.

## 📋 Team Roles Overview

| Role | Vai trò | Input | Output |
|------|---------|-------|--------|
| **CEO** | Tiếp nhận yêu cầu, định hướng | User requirements | Strategic direction |
| **Product Manager** | Phân tích, tạo PRD | User story | PRD document |
| **Architect** | Thiết kế hệ thống | PRD | System design, API specs |
| **Engineer** | Triển khai code | Design docs | Working code |
| **QA Engineer** | Kiểm thử | Code | Test results, Bug reports |
| **DevOps** | Deploy, CI/CD | Release build | Deployed system |

Read roles from: `#file:.github/roles/`

---

## 🔄 Development Pipeline

```
User Request
     ↓
┌─────────────────┐
│   CEO Agent     │ → Strategic analysis & delegation
└────────┬────────┘
         ↓
┌─────────────────┐
│ Product Manager │ → PRD (plans/prd-{feature}.md)
└────────┬────────┘
         ↓
┌─────────────────┐
│   Architect     │ → System Design (plans/design-{feature}.md)
└────────┬────────┘
         ↓
┌─────────────────┐
│   Engineer      │ → Implementation (source code)
└────────┬────────┘
         ↓
┌─────────────────┐
│  QA Engineer    │ → Test & Verify (plans/reports/)
└────────┬────────┘
         ↓
┌─────────────────┐
│    DevOps       │ → Deploy & Monitor
└─────────────────┘
```

---

## 📁 Deliverables Structure

```
plans/
├── prd-{feature-name}.md          # Product Requirements Document
├── design-{feature-name}.md       # System Architecture & Design
├── implementation-{feature-name}.md # Implementation Plan
└── reports/
    ├── qa-report-{feature}.md     # QA Test Results
    ├── code-review-{feature}.md   # Code Review Report
    └── deploy-{feature}.md        # Deployment Report

docs/
├── code-standards.md              # Coding Standards
├── api-documentation.md           # API Docs
├── system-architecture.md         # System Overview
└── project-roadmap.md             # Project Timeline
```

---

## 🎯 Prompt Commands (VS Code Copilot)

| Command | Role Activated | Description |
|---------|---------------|-------------|
| `#file:.github/prompts/plan.prompt.md` | Product Manager | Create PRD from requirements |
| `#file:.github/prompts/design.prompt.md` | Architect | Create system design |
| `#file:.github/prompts/cook.prompt.md` | Full Team | End-to-end implementation |
| `#file:.github/prompts/code.prompt.md` | Engineer | Implement from design |
| `#file:.github/prompts/test.prompt.md` | QA Engineer | Run tests & report |
| `#file:.github/prompts/review.prompt.md` | Code Reviewer | Review code quality |
| `#file:.github/prompts/fix.prompt.md` | Engineer + QA | Debug and fix issues |
| `#file:.github/prompts/git.prompt.md` | DevOps | Git operations |

---

## 📝 Quality Gates

### Gate 1: PRD Review
- [ ] User stories defined
- [ ] Acceptance criteria clear
- [ ] Scope boundaries set
- [ ] Dependencies identified

### Gate 2: Design Review
- [ ] Architecture documented
- [ ] API contracts defined
- [ ] Data models specified
- [ ] Security considered

### Gate 3: Code Review
- [ ] Code standards followed
- [ ] Tests written
- [ ] No security vulnerabilities
- [ ] Performance acceptable

### Gate 4: QA Sign-off
- [ ] All tests passing
- [ ] Edge cases covered
- [ ] No critical bugs
- [ ] Documentation updated

---

## 🚀 Activation (VS Code Copilot)

Để khởi động workflow, sử dụng trong Copilot Chat:

```
@workspace #file:.github/prompts/cook.prompt.md [yêu cầu chi tiết]
```

Hoặc từng bước:
```
@workspace #file:.github/prompts/plan.prompt.md [yêu cầu]     → Tạo PRD
@workspace #file:.github/prompts/design.prompt.md             → Thiết kế hệ thống  
@workspace #file:.github/prompts/code.prompt.md               → Triển khai
@workspace #file:.github/prompts/test.prompt.md               → Kiểm thử
@workspace #file:.github/prompts/review.prompt.md             → Review code
```

---

**Bizino AI DEV** - *Transforming Ideas into Software Automatically*
