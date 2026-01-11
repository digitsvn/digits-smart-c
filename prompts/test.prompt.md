# /test - Run Tests & QA

> **Untested code is broken code**

## 🎯 Purpose
Create and run tests, generate QA report.

## Steps

### 1. Read QA Role
Reference: `#file:.github/roles/qa-engineer.md`

### 2. Test Creation
[AUTO] Create tests for:

**Unit Tests**
- Test each function/method independently
- Mock external dependencies
- Cover edge cases

**Integration Tests**
- Test API endpoints
- Test database operations
- Test component interactions

**E2E Tests** (critical flows)
- Test user journeys
- Test form submissions
- Test error states

### 3. Run Tests
```bash
# Node.js/React
npm test

# Laravel/PHP
php artisan test

# Python
pytest

# Run with coverage
npm test -- --coverage
```

### 4. Coverage Requirements
- Target: > 80% coverage
- Critical paths: 100% coverage
- No uncovered error handlers

### 5. QA Report
Save to: `plans/reports/qa-{feature}.md`

```markdown
# QA Report: {Feature}

## Overview
- **Date**: {current_date}
- **QA Engineer**: QA Agent
- **Feature**: {feature_name}

## Test Summary
| Type | Total | Passed | Failed | Skipped |
|------|-------|--------|--------|---------|
| Unit | {n} | {n} | {n} | {n} |
| Integration | {n} | {n} | {n} | {n} |
| E2E | {n} | {n} | {n} | {n} |

## Coverage
- Overall: {%}
- Branches: {%}
- Functions: {%}
- Lines: {%}

## Issues Found
| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| BUG-01 | High/Med/Low | {desc} | Open/Fixed |

## Test Cases

### TC-01: {Test Name}
- **Type**: Unit/Integration/E2E
- **Input**: {input}
- **Expected**: {expected}
- **Actual**: {actual}
- **Status**: ✅ Pass / ❌ Fail

## Recommendations
- {Recommendation 1}
- {Recommendation 2}

## Sign-off
- [ ] All critical tests passing
- [ ] Coverage meets requirements
- [ ] No high-severity bugs open
```

---

## Example Usage

```
@workspace /test Run tests for the user authentication module

@workspace /test Generate unit tests for src/services/order.ts

@workspace /test Create E2E tests for checkout flow
```
