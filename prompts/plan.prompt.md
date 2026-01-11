# /plan - Create PRD (Product Requirements Document)

> **Planning is half the battle**

## 🎯 Purpose
Create a comprehensive PRD for a new feature or project.

## Input
I need a plan for: `{user_request}`

## Steps

### 1. Request Analysis
- Identify the core problem to solve
- List target users
- Define scope boundaries

### 2. Read PM Role
Reference: `#file:.github/roles/product-manager.md`

### 3. Create PRD

Save to: `plans/prd-{feature-name}.md`

```markdown
# PRD: {Feature Name}

## Overview
- **Date**: {current_date}
- **Author**: Product Manager Agent
- **Status**: Draft
- **Priority**: P0 | P1 | P2 | P3

## Problem Statement
{What problem are we solving?}

## Goals
1. {Primary goal}
2. {Secondary goals}

## Non-Goals (Out of Scope)
- {What we're NOT doing}

## User Stories

### Story 1: {Title}
- **As a**: {user type}
- **I want**: {goal}
- **So that**: {benefit}

**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2

## Requirements

### Functional Requirements
| ID | Requirement | Priority |
|----|------------|----------|
| FR-01 | {description} | Must |
| FR-02 | {description} | Should |

### Non-Functional Requirements
| ID | Requirement | Metric |
|----|------------|--------|
| NFR-01 | {description} | {target} |

## Dependencies
- {External dependencies}
- {Internal dependencies}

## Risks & Mitigation
| Risk | Impact | Mitigation |
|------|--------|------------|
| {risk} | High/Med/Low | {action} |

## Success Metrics
- {Metric 1}: {target}

## Timeline
- Phase 1: {milestone}
- Phase 2: {milestone}
```

### 4. Output Summary
Provide brief summary for handoff to design phase.

---

## Example Usage

```
@workspace /plan Build a user authentication system with OAuth, password reset, and 2FA

@workspace /plan Create a notification service for email, SMS, and push notifications
```
