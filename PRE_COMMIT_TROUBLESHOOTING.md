# Pre-commit Hook Troubleshooting Guide

This guide helps resolve common issues with pre-commit hooks, particularly the ruff-format hook failures.

## 🚨 **Common Issue: "Stashed changes conflicted with hook auto-fixes"**

### **Problem Description**
```
[WARNING] Unstaged files detected.
[INFO] Stashing unstaged files to /Users/user/.cache/pre-commit/patch123456-789.
ruff format..............................................................Failed
- hook id: ruff-format
- files were modified by this hook
[WARNING] Stashed changes conflicted with hook auto-fixes... Rolling back fixes...
```

### **Root Cause**
This happens when:
1. You have **both staged AND unstaged changes** in the same file
2. Pre-commit hooks modify files (formatting, trailing whitespace removal)
3. The modifications conflict with your unstaged changes
4. Pre-commit can't merge the auto-fixes with your stashed changes

### **Solution Steps**

#### **Option 1: Stage All Changes (Recommended)**
```bash
# Check what files have unstaged changes
git status

# Stage all changes before committing
git add .

# Or stage specific files
git add app.py templates/index.html

# Now commit
git commit -m "Your commit message"
```

#### **Option 2: Stash Unstaged Changes**
```bash
# Stash unstaged changes temporarily
git stash push -m "Temporary stash for commit"

# Commit staged changes
git commit -m "Your commit message"

# Restore stashed changes
git stash pop
```

#### **Option 3: Reset and Re-stage**
```bash
# Reset all staged changes
git reset

# Stage only the files you want to commit
git add specific_file.py

# Commit
git commit -m "Your commit message"
```

## 🔧 **Pre-commit Hook Configuration**

### **Current Hooks**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace      # Removes trailing spaces
      - id: end-of-file-fixer       # Ensures files end with newline
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.12.4
    hooks:
      - id: ruff-check              # Linting with auto-fix
        args: [ --fix ]
      - id: ruff-format             # Code formatting
```

### **What Each Hook Does**
- **trailing-whitespace**: Removes spaces at end of lines
- **end-of-file-fixer**: Adds newline at end of files if missing
- **ruff-check**: Lints code and auto-fixes issues
- **ruff-format**: Formats code (line length, indentation, etc.)

## 🛠️ **Best Practices**

### **1. Run Pre-commit Before Staging**
```bash
# Format and check files before staging
ruff format .
ruff check --fix .

# Then stage and commit
git add .
git commit -m "Your message"
```

### **2. Use Pre-commit Manually**
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff-format --all-files

# Run on staged files only
pre-commit run
```

### **3. Check Status Before Committing**
```bash
# Always check what's staged vs unstaged
git status

# See actual changes
git diff --cached  # Staged changes
git diff          # Unstaged changes
```

## 🔍 **Debugging Commands**

### **Check Pre-commit Installation**
```bash
# Verify pre-commit is installed
pre-commit --version

# Check if hooks are installed
ls -la .git/hooks/pre-commit

# Reinstall hooks if needed
pre-commit install
```

### **Test Hooks Manually**
```bash
# Test all hooks
pre-commit run --all-files

# Test specific hook
pre-commit run ruff-format

# Skip hooks for emergency commit
git commit --no-verify -m "Emergency commit"
```

### **View Hook Output**
```bash
# Run with verbose output
pre-commit run --verbose --all-files

# Check what files were modified
git status
git diff
```

## ⚡ **Quick Fix Workflow**

When you encounter the stashed changes conflict:

```bash
# 1. Check status
git status

# 2. Stage all changes
git add .

# 3. Commit (hooks will run automatically)
git commit -m "Your commit message"

# 4. If hooks modify files, they're auto-staged and committed
```

## 🚫 **What NOT to Do**

### **Don't Skip Hooks Regularly**
```bash
# Avoid this unless emergency
git commit --no-verify -m "Skipping hooks"
```

### **Don't Ignore Hook Failures**
- Always fix the underlying issues
- Don't just retry without addressing the conflict

### **Don't Mix Staged/Unstaged Changes**
- Either stage everything or commit in smaller chunks
- Keep your working directory clean

## 📋 **Troubleshooting Checklist**

- [ ] Check `git status` for staged vs unstaged changes
- [ ] Run `pre-commit run --all-files` manually first
- [ ] Stage all changes before committing
- [ ] Verify hooks are installed: `ls .git/hooks/pre-commit`
- [ ] Check pre-commit config: `.pre-commit-config.yaml`
- [ ] Use `git diff` to see what changes hooks made

## 🎯 **Prevention Tips**

1. **Stage incrementally**: Add files as you complete them
2. **Run hooks early**: Use `pre-commit run` during development
3. **Keep working directory clean**: Commit or stash changes regularly
4. **Use IDE integration**: Configure your editor to run ruff on save
5. **Test before committing**: Always run `git status` first

Following these practices will prevent most pre-commit hook conflicts and keep your development workflow smooth!
