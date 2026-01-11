# /fix - Debug & Fix Bugs

> **Debugging is like being a detective in a crime movie where you're also the murderer**

## 🎯 Purpose
Systematic debugging and bug fixing.

## Input
Fix: `{bug_description}`

## Steps

### 1. Understand the Issue
[AUTO] Gather information:
- What is the expected behavior?
- What is the actual behavior?
- Error messages (if any)
- Steps to reproduce

### 2. Debugging Process

**Step 1: Reproduce** 🔄
- Confirm the bug exists
- Document exact steps
- Identify affected components

**Step 2: Isolate** 🔍
- Find the exact location of the bug
- Use binary search if needed
- Check recent changes

**Step 3: Understand** 🧠
- Root cause analysis
- Why did this happen?
- What assumptions were wrong?

**Step 4: Fix** 🔧
- Apply minimal fix
- Don't introduce new bugs
- Consider edge cases

**Step 5: Test** ✅
- Verify fix works
- Test related functionality
- Add regression test

**Step 6: Prevent** 🛡️
- Add test to catch future regressions
- Document if needed
- Consider similar issues elsewhere

### 3. Common Bug Patterns

**Null/Undefined Errors**
```javascript
// Before
const name = user.profile.name;

// After
const name = user?.profile?.name ?? 'Unknown';
```

**Off-by-One Errors**
```javascript
// Before
for (let i = 0; i <= arr.length; i++)

// After
for (let i = 0; i < arr.length; i++)
```

**Race Conditions**
```javascript
// Before
getData();
processData(data);

// After
const data = await getData();
processData(data);
```

**Type Errors**
```javascript
// Before
const total = price + quantity; // "10" + 5 = "105"

// After
const total = Number(price) + Number(quantity); // 15
```

### 4. Fix Report
Save to: `plans/reports/fix-{issue}.md`

```markdown
# Bug Fix Report: {Issue Title}

## Issue
- **ID**: {bug_id}
- **Reported**: {date}
- **Fixed**: {date}
- **Severity**: Critical/High/Medium/Low

## Description
{What was wrong}

## Root Cause
{Why it happened}

## Solution
{How it was fixed}

## Files Changed
| File | Change |
|------|--------|
| {file} | {what changed} |

## Testing
- [ ] Manual testing passed
- [ ] Regression test added
- [ ] Related tests updated

## Prevention
{How to prevent similar issues}
```

---

## Example Usage

```
@workspace /fix TypeError: Cannot read property 'id' of undefined in src/services/user.ts

@workspace /fix Login form not submitting

@workspace /fix API returns 500 error on POST /api/orders
```
