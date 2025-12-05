# Branch Protection Configuration

This document outlines the recommended branch protection rules for this repository.

## Main Branch Protection

### Required Settings

Navigate to: **Settings → Branches → Branch protection rules → Add rule**

#### Branch name pattern
```
main
```

#### Protect matching branches

**✅ Require a pull request before merging**
- Required approvals: **1**
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require review from Code Owners
- ⬜ Restrict who can dismiss pull request reviews
- ⬜ Allow specified actors to bypass required pull requests

**✅ Require status checks to pass before merging**
- ✅ Require branches to be up to date before merging
- **Required status checks:**
  - `CI Pipeline / lint`
  - `CI Pipeline / test (ubuntu-latest, 3.13)`
  - `CI Pipeline / security`
  - `CI Pipeline / build`
  - `CodeQL Analysis / analyze`
  - `Security Scanning / dependency-scan`
  - `Dependency Review / dependency-review` (for PRs only)

**✅ Require conversation resolution before merging**

**✅ Require signed commits**

**✅ Require linear history**
- This enforces squash or rebase merging

**✅ Require deployments to succeed before merging**
- Not applicable for this project

**✅ Lock branch**
- ⬜ Disabled (allows force pushes by admins only)

**✅ Do not allow bypassing the above settings**

**✅ Restrict who can push to matching branches**
- Administrators
- Restrict pushes that create matching branches

**⬜ Allow force pushes**
- Only enable for administrators if needed

**⬜ Allow deletions**
- Keep disabled to prevent accidental branch deletion

---

## Develop Branch Protection (if using)

### Required Settings

#### Branch name pattern
```
develop
```

#### Protect matching branches

**✅ Require a pull request before merging**
- Required approvals: **1**
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ⬜ Require review from Code Owners (optional for develop)

**✅ Require status checks to pass before merging**
- ✅ Require branches to be up to date before merging
- **Required status checks:**
  - `CI Pipeline / lint`
  - `CI Pipeline / test (ubuntu-latest, 3.13)`
  - `CI Pipeline / build`

**✅ Require conversation resolution before merging**

**⬜ Require signed commits** (optional for develop)

**✅ Require linear history**

**⬜ Restrict who can push to matching branches**
- More permissive than main

**⬜ Allow force pushes** (optional for develop)

**⬜ Allow deletions**

---

## Release Branch Protection

### Required Settings

#### Branch name pattern
```
release/*
```

#### Protect matching branches

**✅ Require a pull request before merging**
- Required approvals: **2**
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require review from Code Owners

**✅ Require status checks to pass before merging**
- All CI checks must pass
- Integration tests must pass

**✅ Require signed commits**

**✅ Require linear history**

**✅ Restrict who can push to matching branches**
- Only release managers

**⬜ Allow force pushes**
- Disabled

**⬜ Allow deletions**
- Disabled

---

## Tag Protection

Navigate to: **Settings → Tags → Protected tags → New rule**

### Protected tag pattern
```
v*.*.*
```

### Settings
- ✅ Only allow repository administrators to create matching tags
- This ensures releases are properly controlled

---

## Merge Methods

Navigate to: **Settings → General → Pull Requests**

### Recommended Configuration
- ✅ Allow squash merging
  - Default to pull request title and description
- ⬜ Allow merge commits (disabled)
- ✅ Allow rebase merging
- ✅ Automatically delete head branches

### Merge Button Options
- ✅ Allow auto-merge
- ✅ Always suggest updating pull request branches
- ✅ Allow update branch button

---

## Rulesets (Alternative/Additional)

GitHub's new **Rulesets** feature provides more granular control:

Navigate to: **Settings → Rules → Rulesets → New ruleset**

### Create "Main Branch Protection" Ruleset

**Target:** `main` branch

**Rules:**
1. **Restrict creations** - Nobody can create this branch
2. **Restrict updates** - Only via pull requests
3. **Restrict deletions** - Nobody can delete
4. **Require pull request** 
   - Required approvals: 1
   - Dismiss stale reviews: Yes
   - Require review from Code Owners: Yes
5. **Require status checks**
   - Require branches to be up to date: Yes
   - Status checks: (list all CI checks)
6. **Require signed commits**: Yes
7. **Require linear history**: Yes
8. **Block force pushes**: Yes

**Bypass list:**
- Repository admins (for emergencies only)

---

## Implementation Steps

### 1. Enable Branch Protection
```bash
# Use GitHub CLI to enable protection
gh api repos/tedg-dev/GitHub-SBOM-fetcher/branches/main/protection \
  --method PUT \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_pull_request_reviews[dismiss_stale_reviews]=true \
  --field required_status_checks[strict]=true \
  --field enforce_admins=true \
  --field required_linear_history=true \
  --field allow_force_pushes=false
```

### 2. Configure Required Status Checks
```bash
# Add required checks
gh api repos/tedg-dev/GitHub-SBOM-fetcher/branches/main/protection/required_status_checks \
  --method PATCH \
  --field contexts[]="CI Pipeline / lint" \
  --field contexts[]="CI Pipeline / test (ubuntu-latest, 3.13)" \
  --field contexts[]="CodeQL Analysis / analyze"
```

### 3. Enable Auto-Delete Branches
```bash
gh api repos/tedg-dev/GitHub-SBOM-fetcher \
  --method PATCH \
  --field delete_branch_on_merge=true
```

---

## Monitoring & Compliance

### Weekly Review Checklist
- [ ] Review failed CI checks
- [ ] Check for bypassed protections
- [ ] Verify all PRs have required approvals
- [ ] Ensure signed commits are enforced
- [ ] Check for any direct pushes to protected branches

### Monthly Audit
- [ ] Review branch protection settings
- [ ] Update required status checks if workflows changed
- [ ] Review Code Owners assignments
- [ ] Check for stale branches
- [ ] Verify tag protection is working

---

## Exceptions & Emergency Procedures

### When to Bypass Protection
1. **Critical security fix** requiring immediate deployment
2. **Service outage** requiring immediate hotfix
3. **CI/CD failure** requiring infrastructure fix

### Emergency Bypass Process
1. Document reason in issue
2. Get approval from repository owner
3. Temporarily disable protection
4. Apply fix
5. Re-enable protection immediately
6. Create follow-up PR for proper fix
7. Document incident

---

## Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Rulesets Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets)
- [Requiring Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
