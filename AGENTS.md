# AGENTS.md

## Rules for AI Agents

### 1. No Changes Without Approval

**DO NOT** modify, create, or delete any files without explicit user approval.

**Process:**
1. Explain what you plan to change
2. Wait for user to approve
3. Only then make the change

### 2. Plan Before Implementation

Before any code change:
1. Describe the change
2. Explain why it's needed
3. List affected files
4. Get user approval

### 3. Investigate Before Guessing

**DO NOT** guess at causes. Always investigate:
1. Test the code directly
2. Check logs and errors
3. Compare with working examples
4. Present proven facts, not assumptions

### 4. Commit Rules

**DO NOT** commit changes without explicit user request.

When user says "commit":
1. Show `git status` first
2. List files to be committed
3. Get confirmation
4. Then commit and push

### 5. Config & Secrets

**DO NOT** commit API keys, passwords, or secrets to git.

**Process:**
1. Store secrets in `config.yaml` (gitignored)
2. Provide `config.example.yaml` (without secrets)
3. Add sensitive files to `.gitignore`

### 6. File Changes

Before modifying existing files:
1. Read the current content
2. Explain what will change
3. Show old vs new (if helpful)
4. Get approval

### 7. New Files

Before creating new files:
1. Explain the purpose
2. Show where it fits in project structure
3. Get approval

---

## Summary

| Action | Requires Approval |
|--------|-------------------|
| Modify existing file | Yes |
| Create new file | Yes |
| Delete file | Yes |
| Commit changes | Yes |
| Push to remote | Yes |
| Run commands (make, docker) | No (safe operations) |
| Read files | No |
| Search codebase | No |
