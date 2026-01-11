# /git - Git Workflow

> **Commit early, commit often, but commit wisely**

## 🎯 Purpose
Standardized Git workflow for commits, pushes, and PRs.

## Steps

### 1. Pre-Commit Checks
[AUTO] Run before committing:

```bash
# Check for changes
git status

# Run tests
npm test || php artisan test || pytest

# Run linting
npm run lint || php artisan pint

# Check for sensitive data
git diff --cached | grep -E "(password|secret|api_key|token)" && echo "⚠️ Check for sensitive data!"
```

### 2. Commit Message Format

**Conventional Commits:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Refactoring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```bash
git commit -m "feat(auth): add OAuth2 login support"
git commit -m "fix(cart): resolve quantity update bug"
git commit -m "docs(api): update endpoint documentation"
git commit -m "refactor(services): extract common utilities"
```

### 3. Branch Strategy

**Branch Naming:**
```
feature/{feature-name}
fix/{bug-description}
hotfix/{critical-fix}
release/{version}
```

**Workflow:**
```
main (production)
  └── develop
       ├── feature/user-auth
       ├── feature/payment
       └── fix/login-bug
```

### 4. Push Process
[AUTO] Execute:

```bash
# Stage all changes
git add .

# Commit with message
git commit -m "{conventional_commit_message}"

# Push to remote
git push origin {current_branch}
```

### 5. Pull Request Template

```markdown
## Description
{What does this PR do?}

## Related Issue
Fixes #{issue_number}

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No sensitive data committed

## Screenshots (if applicable)
{Add screenshots}

## Testing Instructions
1. {Step 1}
2. {Step 2}
```

### 6. Merge Strategy

**For features:**
```bash
# Squash and merge
git checkout develop
git merge --squash feature/my-feature
git commit -m "feat(scope): description"
```

**For releases:**
```bash
# Create release branch
git checkout -b release/v1.0.0
git push origin release/v1.0.0

# After testing, merge to main
git checkout main
git merge release/v1.0.0
git tag v1.0.0
git push origin main --tags
```

---

## ⚠️ Safety Rules

- **NEVER** commit `.env` files
- **NEVER** commit API keys or passwords
- **ALWAYS** review `git diff` before committing
- **ALWAYS** pull before pushing

---

## Example Usage

```
@workspace /git Commit all changes with appropriate message

@workspace /git Create PR for feature/payment-integration

@workspace /git Push current branch to remote
```
