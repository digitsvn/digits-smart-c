# /code - Implement Code

> **Clean code is not written by following rules. It is written by knowing them.**

## 🎯 Purpose
Implement code according to design document.

## Input
Implement: `{feature_name}` based on `plans/design-{feature}.md`

## Steps

### 1. Read Design Document
Read the design file for implementation details.

### 2. Read Engineer Role
Reference: `#file:.github/roles/engineer.md`

### 3. Implementation Order
[AUTO] Execute in this order:

1. **Database Models/Migrations**
   - Create database schemas
   - Run migrations

2. **Core Business Logic**
   - Services/Use cases
   - Domain models

3. **API Controllers/Routes**
   - Endpoints
   - Request validation

4. **Frontend Components** (if applicable)
   - UI components
   - State management

5. **Error Handling**
   - Input validation
   - Error responses

### 4. Coding Standards

**The Holy Trinity:**
- **YAGNI**: Only implement what's needed
- **KISS**: Keep it simple
- **DRY**: Don't repeat yourself

**Quality Standards:**
- File size: < 200 lines
- Function size: < 50 lines
- Descriptive naming
- Comments explain WHY, not WHAT

### 5. Post-Implementation Checklist
```
- [ ] No syntax errors
- [ ] Follows naming conventions
- [ ] Has proper error handling
- [ ] Tests written
- [ ] No hardcoded secrets
- [ ] No console.log (use proper logging)
```

---

## 🎨 UI Framework Rules

### Existing Projects
- Follow existing framework (check `package.json`)
- Maintain consistent styling

### New Projects / React Admin
- **REQUIRED**: use **Semi Design**
- Install: `npm install @douyinfe/semi-ui`

```jsx
import { Table, Form, Button, Card, Modal } from '@douyinfe/semi-ui';

export function UserList() {
  return (
    <Card title="Users">
      <Table columns={columns} dataSource={data} />
    </Card>
  );
}
```

---

## Example Usage

```
@workspace /code Implement the user authentication from plans/design-user-auth.md

@workspace /code Build the CRUD endpoints for products

@workspace /code Create React components for the dashboard
```
