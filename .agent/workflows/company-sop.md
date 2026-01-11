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

## 🎯 Workflow Commands

| Command | Role Activated | Description |
|---------|---------------|-------------|
| `/plan` | Product Manager | Create PRD from requirements |
| `/design` | Architect | Create system design |
| `/cook` | Full Team | End-to-end implementation |
| `/code` | Engineer | Implement from design |
| `/test` | QA Engineer | Run tests & report |
| `/review` | Code Reviewer | Review code quality |
| `/deploy` | DevOps | Deploy to environment |
| `/fix` | Engineer + QA | Debug and fix issues |

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

## 🚀 Activation

Để khởi động workflow, sử dụng:
```
/cook [yêu cầu chi tiết]
```

Hoặc từng bước:
```
/plan [yêu cầu]     → Tạo PRD
/design             → Thiết kế hệ thống  
/code               → Triển khai
/test               → Kiểm thử
/review             → Review code
/deploy             → Triển khai
```
