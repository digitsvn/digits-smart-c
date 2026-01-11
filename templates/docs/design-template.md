# System Design Template

## Document Info
- **Feature**: {Feature Name}
- **PRD Reference**: plans/prd-{feature}.md
- **Date**: {YYYY-MM-DD}
- **Architect**: Architect Agent
- **Status**: Draft | Review | Approved

---

## Context

### Problem Summary
{Brief summary of what we're building and why}

### Requirements Summary
- FR-01: {key requirement}
- NFR-01: {key non-functional requirement}

---

## Architecture Overview

### High-Level Design
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▸│     API     │────▸│  Database   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Cache     │
                    └─────────────┘
```

### Components
| Component | Responsibility | Technology |
|-----------|---------------|------------|
| {name} | {what it does} | {tech stack} |

---

## API Design

### Endpoints Overview
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/{resource} | Create new |
| GET | /api/{resource}/{id} | Get by ID |
| PUT | /api/{resource}/{id} | Update |
| DELETE | /api/{resource}/{id} | Delete |

### Endpoint Details

#### `POST /api/{resource}`

**Description**: {What this endpoint does}

**Authentication**: Required / Optional

**Request Headers**:
| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | Bearer token |

**Request Body**:
```json
{
  "field1": "string",
  "field2": 123
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "data": {
    "id": "123",
    "field1": "string"
  }
}
```

**Error Responses**:
| Code | Message | When |
|------|---------|------|
| 400 | Validation error | Invalid input |
| 401 | Unauthorized | Missing token |
| 404 | Not found | Resource not found |

---

## Data Models

### Entity Relationship Diagram
```
┌───────────┐       ┌───────────┐
│   User    │──────▸│   Order   │
└───────────┘       └───────────┘
                          │
                          ▼
                    ┌───────────┐
                    │ OrderItem │
                    └───────────┘
```

### {Entity} Schema
```sql
CREATE TABLE {entity} (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(255) NOT NULL,
    status      ENUM('active', 'inactive') DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_{entity}_status ON {entity}(status);
```

---

## Security Considerations

- [ ] **Authentication**: JWT tokens with refresh
- [ ] **Authorization**: Role-based access control
- [ ] **Input Validation**: All inputs validated
- [ ] **SQL Injection**: Parameterized queries
- [ ] **XSS**: Output encoding
- [ ] **Rate Limiting**: 100 req/min per user

---

## Performance Considerations

### Expected Load
- Peak requests: {n} req/sec
- Average response time: < 200ms

### Caching Strategy
| Data | TTL | Cache Type |
|------|-----|------------|
| {data} | 5 min | Redis |

### Database Optimization
- Indexes on: {columns}
- Query optimization: {notes}

---

## Implementation Plan

### Phase 1: Core
1. Database migrations
2. Basic CRUD APIs
3. Unit tests

### Phase 2: Enhancement
1. Caching
2. Performance optimization
3. Integration tests

---

## File Structure
```
src/
├── controllers/
│   └── {feature}/
│       └── {feature}.controller.{ext}
├── services/
│   └── {feature}/
│       └── {feature}.service.{ext}
├── models/
│   └── {entity}.{ext}
├── repositories/
│   └── {entity}.repository.{ext}
└── tests/
    └── {feature}/
```

---

## Migration Plan

1. Create database schema
2. Deploy API (backward compatible)
3. Migrate data (if needed)
4. Switch traffic
5. Monitor

### Rollback Plan
1. Revert API deployment
2. Restore database (if needed)
3. Notify stakeholders

---

## Open Questions

- [ ] {Technical question 1}
- [ ] {Decision needed on X}
