# /review - Code Review

> **Code reviewed by many is better than code written by one**

## 🎯 Purpose
Comprehensive code review for quality, security, and best practices.

## Steps

### 1. Read Code Reviewer Role
Reference: `#file:.github/roles/code-reviewer.md`

### 2. Review Areas

**Security** 🔐
- [ ] No hardcoded credentials
- [ ] Input validation present
- [ ] SQL injection prevention
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Proper authentication/authorization

**Performance** ⚡
- [ ] No N+1 queries
- [ ] Appropriate caching
- [ ] Lazy loading where needed
- [ ] Efficient algorithms
- [ ] No memory leaks

**Code Quality** 📝
- [ ] Follows naming conventions
- [ ] DRY principle applied
- [ ] SOLID principles followed
- [ ] Appropriate error handling
- [ ] Readable code structure

**Tests** 🧪
- [ ] Unit tests present
- [ ] Edge cases covered
- [ ] Mocks used appropriately
- [ ] Tests are meaningful

**Documentation** 📖
- [ ] Code comments where needed
- [ ] API documentation updated
- [ ] README updated if needed

### 3. Review Report
Save to: `plans/reports/review-{feature}.md`

```markdown
# Code Review Report: {Feature}

## Overview
- **Date**: {current_date}
- **Reviewer**: Code Reviewer Agent
- **Files Reviewed**: {count}

## Summary
| Category | Score | Notes |
|----------|-------|-------|
| Security | {1-10} | {notes} |
| Performance | {1-10} | {notes} |
| Code Quality | {1-10} | {notes} |
| Tests | {1-10} | {notes} |
| Documentation | {1-10} | {notes} |
| **Overall** | {avg}/10 | |

## Issues Found

### Critical 🔴
| File | Line | Issue | Suggestion |
|------|------|-------|------------|
| {file} | {line} | {issue} | {fix} |

### Major 🟠
| File | Line | Issue | Suggestion |
|------|------|-------|------------|
| {file} | {line} | {issue} | {fix} |

### Minor 🟡
| File | Line | Issue | Suggestion |
|------|------|-------|------------|
| {file} | {line} | {issue} | {fix} |

## Positive Highlights
- ✨ {Good practice found}
- ✨ {Well-structured code}

## Action Items
1. [ ] {Required fix 1} - CRITICAL
2. [ ] {Required fix 2} - MAJOR
3. [ ] {Suggested improvement} - MINOR

## Conclusion
{Overall assessment and recommendation}

**Approval Status**: ✅ Approved / ⚠️ Approved with changes / ❌ Needs rework
```

---

## Example Usage

```
@workspace /review Review the latest changes in src/services/

@workspace /review Security review for authentication module

@workspace /review Review PR #123
```
