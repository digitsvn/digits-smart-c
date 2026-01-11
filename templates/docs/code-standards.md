# Development Rules & Standards

> **Version**: 1.0.0  
> **Last Updated**: 2025-12-28

## 🎯 Core Principles

### The Holy Trinity
| Principle | Meaning | Example |
|-----------|---------|---------|
| **YAGNI** | You Aren't Gonna Need It | Don't add features "just in case" |
| **KISS** | Keep It Simple, Stupid | Simplest solution that works |
| **DRY** | Don't Repeat Yourself | Extract common code into utilities |

## 📁 File Conventions

### Naming
- **Files**: `kebab-case` (e.g., `user-authentication.ts`)
- **Classes**: `PascalCase` (e.g., `UserService`)
- **Functions**: `camelCase` (e.g., `getUserById`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)

### Size Limits
- **File**: < 200 lines (split if larger)
- **Function**: < 50 lines
- **Line length**: < 120 characters

## 🏗️ Architecture

### Project Structure
```
src/
├── controllers/     # HTTP request handlers
├── services/        # Business logic
├── models/          # Data models
├── repositories/    # Data access layer
├── utils/           # Utility functions
├── middlewares/     # Request middlewares
├── config/          # Configuration
└── tests/           # Test files
```

### Layer Responsibilities
| Layer | Responsibility | Depends On |
|-------|---------------|------------|
| Controller | Request/Response handling | Service |
| Service | Business logic | Repository, Utils |
| Repository | Data access | Database |
| Model | Data structure | - |

## ✅ Code Quality

### Error Handling
```javascript
// ✅ Good
try {
  const result = await riskyOperation();
  return result;
} catch (error) {
  logger.error('Operation failed', { error, context });
  throw new AppError('OPERATION_FAILED', error.message);
}

// ❌ Bad
try {
  return await riskyOperation();
} catch (e) {
  console.log(e); // Don't use console.log
  // Don't swallow errors silently
}
```

### Input Validation
- Always validate inputs at entry points
- Use proper validation libraries
- Return meaningful error messages

### Security
- [ ] Never hardcode secrets
- [ ] Always sanitize user inputs
- [ ] Use parameterized queries
- [ ] Implement proper authentication
- [ ] Log security events

## 🧪 Testing

### Requirements
- Minimum coverage: 80%
- All critical paths tested
- Edge cases covered
- No mocks for critical integration points

### Test Naming
```javascript
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with valid data', () => {});
    it('should throw error when email exists', () => {});
  });
});
```

## 📝 Documentation

### Code Comments
```javascript
// ✅ Good - explains WHY
// Use exponential backoff to avoid overwhelming the API
const delay = Math.pow(2, retryCount) * 1000;

// ❌ Bad - explains WHAT (obvious from code)
// Multiply retry count by 1000
const delay = retryCount * 1000;
```

### Function Documentation
```javascript
/**
 * Creates a new user in the system
 * 
 * @param userData - User registration data
 * @returns Created user object
 * @throws {ValidationError} When email is invalid
 * @throws {ConflictError} When email already exists
 */
async function createUser(userData: CreateUserDTO): Promise<User> {}
```

## 🔄 Git Workflow

### Commit Messages
```
{type}({scope}): {subject}

Types: feat, fix, docs, style, refactor, test, chore
Examples:
- feat(auth): add password reset functionality
- fix(api): handle null response gracefully
```

### Pre-commit Checklist
- [ ] Code compiles without errors
- [ ] All tests pass
- [ ] No linting errors
- [ ] No sensitive data committed
- [ ] Meaningful commit message

## 🚫 Anti-patterns to Avoid

| Anti-pattern | Problem | Solution |
|--------------|---------|----------|
| God Class | Too many responsibilities | Split into focused classes |
| Magic Numbers | Unclear meaning | Use named constants |
| Deep Nesting | Hard to read | Early returns, extract functions |
| Copy-Paste | Maintenance nightmare | Extract reusable code |
| Silent Failures | Hidden bugs | Proper error handling |
