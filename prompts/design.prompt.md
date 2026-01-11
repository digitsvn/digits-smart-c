# /design - System Design

> **Good architecture = scalable, maintainable, secure code**

## 🎯 Purpose
Create technical design from PRD.

## Input
Design for: `{feature_name}` based on PRD at `plans/prd-{feature}.md`

## Steps

### 1. Read PRD
Read the PRD file for the feature.

### 2. Read Architect Role  
Reference: `#file:.github/roles/architect.md`

### 3. Create Design Document

Save to: `plans/design-{feature-name}.md`

```markdown
# System Design: {Feature Name}

## Context
- **PRD Reference**: plans/prd-{feature}.md
- **Date**: {current_date}
- **Architect**: Architect Agent
- **Status**: Draft

## Architecture Overview

### High-Level Design
```
[Component Diagram - ASCII]
```

### Components
| Component | Responsibility | Technology |
|-----------|---------------|------------|
| {name} | {desc} | {tech} |

## API Design

### Endpoints

#### `POST /api/{resource}`
- **Description**: {what it does}
- **Authentication**: Required/Optional
- **Request Body**:
  ```json
  {
    "field": "type"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "data": {}
  }
  ```
- **Error Codes**:
  | Code | Message |
  |------|---------|
  | 400 | Bad Request |
  | 401 | Unauthorized |

## Data Models

### {Entity} Schema
```sql
CREATE TABLE {entity} (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  ...
);
```

### Relationships
- {Entity A} → {Entity B}: {one-to-many/many-to-many}

## Security Considerations
- [ ] Authentication method
- [ ] Authorization rules
- [ ] Input validation
- [ ] Data encryption
- [ ] Rate limiting

## Performance Considerations
- Expected load: {requests/sec}
- Caching strategy: {approach}
- Database indexing: {key indexes}

## File Structure
```
src/
├── controllers/
│   └── {feature}/
├── services/
│   └── {feature}/
├── models/
│   └── {entity}.{ext}
└── tests/
    └── {feature}/
```

## Implementation Notes

### Phase 1: Core
- {Component 1}: {implementation notes}

### Phase 2: Enhancement  
- {Feature}: {notes}

## Dependencies
- External: {APIs, services}
- Internal: {existing modules}
```

### 4. Output Implementation Order
Provide suggested sequence for development.

---

## 🎨 UI Framework Selection

### Existing Projects
- Analyze `package.json` for current UI library
- Follow existing patterns

### New Projects / React Admin
- **REQUIRED**: use **Semi Design**
- Install: `npm install @douyinfe/semi-ui`
- Docs: https://semi.design

---

## Example Usage

```
@workspace /design Design the system for plans/prd-user-auth.md

@workspace /design Create architecture for the inventory management API
```
