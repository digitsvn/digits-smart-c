---
description: 🔥 Full Auto Pipeline - Từ yêu cầu đến MVP hoàn chỉnh
---

# /cook - Bizino AI DEV Full Auto Pipeline

> **"Từ yêu cầu khách hàng → MVP chạy được"**

## 🎯 Mục Đích
Pipeline tự động hoàn toàn: Nhận yêu cầu → Phân tích → Thiết kế → Code → Test → Review → Triển khai

## ⚡ Workflow
// turbo-all

### Phase 0: 📝 Phân Tích Yêu Cầu

**Đọc yêu cầu từ khách hàng và phân tích:**

```markdown
## Request Analysis
- Domain: {e-commerce/saas/social/erp/custom}
- Core Entities: {list}
- Core Features: {list}
- Users: {list roles}
- Tech Stack: {recommendation}
- Complexity: {simple/medium/complex}
- Estimated Time: {hours}
```

**Clarification (nếu cần):**
- Sử dụng AskUserQuestion tool để hỏi thêm chi tiết
- Hỏi tối đa 3 câu quan trọng nhất

---

### Phase 1: 📋 Product Manager - PRD Creation

```bash
# Load PM role
cat .agent/roles/product-manager.md
```

**Actions:**
1. Phân tích yêu cầu chi tiết
2. Tạo PRD tại `plans/prd-{feature}.md`:
   - Problem Statement
   - Goals & Non-Goals
   - User Stories với Acceptance Criteria
   - Functional Requirements
   - Non-Functional Requirements
   - Success Metrics
3. Output summary

---

### Phase 2: 🏗️ Architect - System Design

```bash
# Load Architect role
cat .agent/roles/architect.md
```

**Actions:**
1. Đọc PRD
2. Thiết kế architecture:
   - High-level diagram
   - Component breakdown
   - API endpoints
   - Database schema
   - Tech stack confirmation
3. Tạo Design Doc tại `plans/design-{feature}.md`
4. Output implementation order

---

### Phase 3: 👨‍💻 Engineer - Implementation

```bash
# Load Engineer role
cat .agent/roles/engineer.md
```

**Actions:**
1. Implement theo thứ tự:
   - Database models/migrations
   - Core business logic
   - API endpoints
   - Frontend components
   - Error handling
2. Viết code theo best practices:
   - YAGNI, KISS, DRY
   - Clean code
   - Proper validation
3. Sau mỗi file, chạy syntax check

---

### Phase 4: 🧪 QA Engineer - Auto Testing

```bash
# Load QA role
cat .agent/roles/qa-engineer.md
```

**Actions:**
1. Tự động tạo tests:
   - Unit tests cho mỗi function
   - Integration tests cho APIs
   - E2E tests cho critical flows
2. Chạy test suite
3. Đảm bảo coverage > 80%
4. Tạo QA Report tại `plans/reports/qa-{feature}.md`

```bash
# Run tests
npm test 2>/dev/null || php artisan test 2>/dev/null || pytest 2>/dev/null
```

---

### Phase 5: 👁️ Code Reviewer - Quality Check

```bash
# Load Reviewer role
cat .agent/roles/code-reviewer.md
```

**Actions:**
1. Review tất cả code changes:
   - Security vulnerabilities
   - Performance issues
   - Code quality
   - Best practices
2. Tạo Review Report
3. Fix critical issues (nếu có)

---

### Phase 6: 🚀 DevOps - Deployment (Optional)

```bash
# Load DevOps role
cat .agent/roles/devops.md
```

**Actions:**
1. Prepare deployment:
   - Create/update Dockerfile
   - Create/update docker-compose
   - Create/update CI/CD pipeline
2. Environment setup guide
3. Deployment instructions

---

### Phase 7: 📊 Final Report

**Output Format:**

```
╔═══════════════════════════════════════════════════════════════════╗
║      🚀 BIZINO AI DEV - MVP COMPLETE                              ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  📋 Project: {Feature Name}                                        ║
║  ⏱️  Time: {duration}                                              ║
║  📁 Files: {count} created/modified                                ║
║                                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  📄 DOCUMENTS                                                      ║
║  ├── PRD: plans/prd-{feature}.md                                  ║
║  ├── Design: plans/design-{feature}.md                            ║
║  └── Reports: plans/reports/                                       ║
║                                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  💻 CODE                                                           ║
║  ├── Files created: {list}                                        ║
║  ├── Tests: {pass}/{total} passing                                ║
║  └── Coverage: {%}                                                 ║
║                                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  ✅ QUALITY                                                        ║
║  ├── Code Review: PASSED                                          ║
║  ├── Security: No vulnerabilities                                 ║
║  └── Performance: Optimized                                        ║
║                                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  🚀 DEPLOYMENT                                                     ║
║  ├── Ready for: {staging/production}                              ║
║  └── Run: {deployment command}                                     ║
║                                                                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  📖 NEXT STEPS                                                     ║
║  1. Review generated code                                          ║
║  2. Configure environment variables                                ║
║  3. Deploy to staging                                              ║
║  4. User acceptance testing                                        ║
║                                                                    ║
╚═══════════════════════════════════════════════════════════════════╝

❓ Unresolved Questions (if any):
- {Question 1}
```

---

## 🎯 Example Usage

```bash
# E-commerce MVP
/cook Build an online store with product catalog, shopping cart, user auth, and Stripe checkout

# SaaS Dashboard
/cook Create a project management tool like Trello with boards, cards, drag-drop, and team collaboration

# API Service
/cook Build a REST API for inventory management with products, categories, stock tracking
```

---

## ⚙️ Configuration

Tùy chỉnh behavior trong `.agent/project.json`:

```json
{
  "auto_deploy": false,
  "auto_commit": true,
  "test_coverage_min": 80,
  "code_review_strict": true
}
```

---

## 🛑 Error Handling

Nếu bất kỳ phase nào fail:
1. Document the issue
2. Attempt auto-fix (1 lần)
3. Nếu vẫn fail → Ask user for guidance
4. Continue sau khi resolved

---

**Bizino AI DEV** - *Transforming Ideas into Software Automatically*
