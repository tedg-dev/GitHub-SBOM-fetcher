# CI/CD Pipeline Checks Documentation

## Overview

This document explains all CI/CD checks that run on this repository, including which checks are expected to be skipped and why.

---

## 📊 Check Summary

| Category | Total Checks | Always Run | Conditionally Run |
|----------|-------------|------------|-------------------|
| **Test Suites** | 6 | 6 | 0 |
| **Security Scans** | 5 | 5 | 0 |
| **Code Quality** | 3 | 3 | 0 |
| **Build & Integration** | 3 | 2 | 1 |
| **Automation** | 2 | 0 | 2 |
| **TOTAL** | **19** | **16** | **3** |

---

## ✅ Checks That Always Run

### Test Suites (6 checks)
All combinations of OS and Python versions:

1. **Test Suite (ubuntu-latest, 3.11)**
2. **Test Suite (ubuntu-latest, 3.12)**
3. **Test Suite (ubuntu-latest, 3.13)**
4. **Test Suite (macos-latest, 3.11)**
5. **Test Suite (macos-latest, 3.12)**
6. **Test Suite (macos-latest, 3.13)**

**Purpose:** Ensure code works across different operating systems and Python versions.

---

### Security Scans (5 checks)

1. **CodeQL Security Analysis (python)** - Static code analysis for vulnerabilities
2. **Trivy Container Scan** - Container and filesystem vulnerability scanning
3. **Secret Scanning** (TruffleHog) - Detect accidentally committed secrets
4. **Dependency Security Scan** - Check dependencies for known vulnerabilities
5. **License Compliance Check** - Ensure dependencies have acceptable licenses

**Purpose:** Prevent security vulnerabilities and license violations.

---

### Code Quality (3 checks)

1. **Code Quality & Linting**
   - Black (code formatting)
   - isort (import sorting)
   - flake8 (linting)
   - mypy (type checking - non-blocking)
   - pylint (additional linting)

2. **Code Security Analysis** (Bandit)
   - Scans Python code for security anti-patterns

3. **Review Dependencies** (Dependency Review Action)
   - Reviews dependency changes in PRs

**Purpose:** Maintain code quality and consistency.

---

### Build (2 checks)

1. **Build Package** - Builds Python distribution packages
2. **CI Status Check** - Overall pipeline status aggregator

**Purpose:** Ensure package can be built and distributed.

---

## ⏭️ Conditionally Run Checks (3 checks)

### 1. Integration Test ✅ (NOW RUNS IN PRS!)

**Condition:** 
```yaml
if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/main')
```

**When it runs:**
- ✅ In pull requests (for pre-merge validation)
- ✅ On direct pushes to main branch

**When it's skipped:**
- On pushes to other branches
- On other event types (schedule, workflow_dispatch, etc.)

**Why:** Integration tests validate the full application workflow. Running in PRs prevents broken code from reaching main.

---

### 2. Auto Approve Dependabot ⏭️ (CONDITIONAL)

**Condition:**
```yaml
if: github.actor == 'dependabot[bot]'
```

**When it runs:**
- ✅ Only for PRs created by Dependabot

**When it's skipped:**
- ❌ All user-created PRs
- ❌ All pushes to branches

**Why:** This is an automation helper that only applies to Dependabot PRs. It's always skipped for human-created PRs, which is expected behavior.

---

### 3. Auto Merge PR ⏭️ (CONDITIONAL)

**Condition:**
```yaml
if: github.event_name == 'pull_request' && (github.actor == 'dependabot[bot]' || contains(github.event.pull_request.labels.*.name, 'automerge'))
```

**When it runs:**
- ✅ For Dependabot PRs (if configured)
- ✅ For PRs with 'automerge' label

**When it's skipped:**
- ❌ All normal PRs without 'automerge' label

**Why:** This is an automation helper for specific scenarios. Normal PRs are merged manually, so skipping is expected.

---

## 🎯 Expected Results for Normal PRs

When you create a typical PR, you should expect:

### ✅ Passing (16-19 checks)
- 6 test suite checks
- 5 security scan checks
- 3 code quality checks
- 1 build check
- 1 CI status check
- 1 integration test (NEW!)

### ⏭️ Skipped (2-3 checks)
- Auto Approve Dependabot (always skipped for user PRs)
- Auto Merge PR (skipped unless labeled)
- Integration Test (now runs in PRs, but may skip in other contexts)

### Total: **18-22 checks** per PR
- **16-19 passing** = ✅ GOOD
- **2-3 skipped** = ✅ EXPECTED
- **0 failed** = ✅ PERFECT

---

## 🔧 Recent Improvements

### PR #11: Integration Test Pre-Merge Validation

**Problem:**
Integration tests only ran AFTER merging to main, meaning broken integration code could be merged.

**Solution:**
Changed condition to run integration tests in PRs:
```yaml
# Before:
if: github.event_name == 'push' && github.ref == 'refs/heads/main'

# After:
if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/main')
```

**Benefit:**
✅ Integration tests now validate code BEFORE merge
✅ Prevents broken integration code from reaching main
✅ Maintains testing on main branch pushes

---

## 📈 CI/CD Pipeline Flow

```
┌─────────────────┐
│  Pull Request   │
│   or Push to    │
│      Main       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Code Quality & Linting (1 check)      │
│  - Black, isort, flake8, mypy, pylint  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Test Suites (6 checks)                 │
│  - Ubuntu: Python 3.11, 3.12, 3.13     │
│  - macOS:  Python 3.11, 3.12, 3.13     │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Security Scans (5 checks)              │
│  - CodeQL, Trivy, Secrets, Deps, Lic   │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Build Package (1 check)                │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Integration Test (1 check)             │
│  - Runs in PRs + main pushes            │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  CI Status Check (1 check)              │
│  - Aggregate status of all checks       │
└─────────────────────────────────────────┘
```

---

## 🚨 Troubleshooting

### "Why are 3 checks skipped?"

**Answer:** This is expected! The 3 conditionally-run checks are:
1. **Auto Approve Dependabot** - Only runs for Dependabot PRs
2. **Auto Merge PR** - Only runs if labeled with 'automerge'
3. **Integration Test** - Now runs in PRs (recently fixed!)

### "How many checks should pass?"

**For normal PRs:** Expect 18-19 passing checks
- If you see 16-19 passing and 2-3 skipped = ✅ **PERFECT**
- If you see failures = ❌ **Needs attention**

### "Integration test is failing on main"

If integration tests fail on main but passed in the PR:
1. Check if dependencies changed between PR and merge
2. Verify environment setup is correct
3. Review integration test logs for specifics

---

## 📚 Related Documentation

- **CI/CD Workflows:** `.github/workflows/`
- **Test Coverage:** See `pytest.ini` for coverage requirements (95%+)
- **Security Config:** `.github/workflows/security.yml`
- **Code Quality Config:** `.flake8`, `pyproject.toml`

---

## 🔄 Continuous Improvement

This CI/CD pipeline is designed to:
- ✅ Catch issues early (pre-merge)
- ✅ Maintain high code quality (96%+ coverage)
- ✅ Ensure security (multiple scan layers)
- ✅ Validate across platforms (Ubuntu + macOS)
- ✅ Support multiple Python versions (3.11-3.13)

**Last Updated:** December 5, 2025 (PR #11)
