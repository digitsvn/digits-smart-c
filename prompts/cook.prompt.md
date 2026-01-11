# /cook - Bizino AI DEV Full Auto Pipeline

> **"From customer request → Working MVP"**

## 🎯 Purpose
Fully automated pipeline: Receive request → Analyze → Design → Code → Test → Review → Deploy

## ⚡ Execution Mode
[TURBO] - All steps run automatically

---

## Phase 0: 📝 Request Analysis

**Read and analyze customer request:**

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

**Clarification (if needed):**
- Ask maximum 3 most important questions
- Confirm understanding before proceeding

---

## Phase 1: 📋 Product Manager - PRD Creation

Read role: `#file:.github/roles/product-manager.md`

**Actions:**
1. Analyze detailed requirements
2. Create PRD at `plans/prd-{feature}.md`:
   - Problem Statement
   - Goals & Non-Goals
   - User Stories with Acceptance Criteria
   - Functional Requirements
   - Non-Functional Requirements
   - Success Metrics
3. Output summary

---

## Phase 2: 🏗️ Architect - System Design

Read role: `#file:.github/roles/architect.md`

**Actions:**
1. Read PRD
2. Design architecture:
   - High-level diagram
   - Component breakdown
   - API endpoints
   - Database schema
   - Tech stack confirmation
3. Create Design Doc at `plans/design-{feature}.md`
4. Output implementation order

---

## Phase 3: 👨‍💻 Engineer - Implementation

Read role: `#file:.github/roles/engineer.md`

**Actions:**
1. Implement in order:
   - Database models/migrations
   - Core business logic
   - API endpoints
   - Frontend components
   - Error handling
2. Follow best practices:
   - YAGNI, KISS, DRY
   - Clean code
   - Proper validation
3. Run syntax check after each file

---

## Phase 4: 🧪 QA Engineer - Auto Testing

Read role: `#file:.github/roles/qa-engineer.md`

**Actions:**
1. Auto-generate tests:
   - Unit tests for each function
   - Integration tests for APIs
   - E2E tests for critical flows
2. Run test suite
3. Ensure coverage > 80%
4. Create QA Report at `plans/reports/qa-{feature}.md`

```bash
# Run tests
npm test || php artisan test || pytest
```

---

## Phase 5: 👁️ Code Reviewer - Quality Check

Read role: `#file:.github/roles/code-reviewer.md`

**Actions:**
1. Review all code changes:
   - Security vulnerabilities
   - Performance issues
   - Code quality
   - Best practices
2. Create Review Report
3. Fix critical issues (if any)

---

## Phase 6: 🚀 DevOps - Deployment (Optional)

Read role: `#file:.github/roles/devops.md`

**Actions:**
1. Prepare deployment:
   - Create/update Dockerfile
   - Create/update docker-compose
   - Create/update CI/CD pipeline
2. Environment setup guide
3. Deployment instructions

---

## Phase 7: 📊 Final Report

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
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 🎯 Example Usage

```
@workspace /cook Build an online store with product catalog, shopping cart, user auth, and Stripe checkout

@workspace /cook Create a project management tool like Trello with boards, cards, drag-drop

@workspace /cook Build a REST API for inventory management with products, categories, stock tracking
```

---

## 🛑 Error Handling

If any phase fails:
1. Document the issue
2. Attempt auto-fix (1 time)
3. If still fails → Ask user for guidance
4. Continue after resolved

---

**Bizino AI DEV** - *Transforming Ideas into Software Automatically*
