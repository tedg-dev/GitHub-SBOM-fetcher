# CI/CD Pipeline Documentation

Complete guide to the GitHub-SBOM-fetcher CI/CD infrastructure.

---

## 🎯 Overview

This repository has a **production-grade CI/CD pipeline** with:
- ✅ Automated testing on every push/PR
- ✅ Security scanning (CodeQL, Dependabot, Bandit, Safety)
- ✅ Automated releases with semantic versioning
- ✅ Auto-labeling and auto-merge capabilities
- ✅ Comprehensive code quality gates
- ✅ Multi-platform testing (Ubuntu, macOS)
- ✅ Multiple Python versions (3.11, 3.12, 3.13)

---

## 📁 CI/CD Structure

```
.github/
├── workflows/
│   ├── ci.yml                    # Main CI pipeline (lint, test, build)
│   ├── release.yml               # Automated releases
│   ├── security.yml              # Security scans
│   ├── codeql.yml                # CodeQL analysis
│   ├── label-pr.yml              # Auto-label PRs
│   ├── auto-merge.yml            # Auto-merge approved PRs
│   └── dependency-review.yml     # Review PR dependencies
├── ISSUE_TEMPLATE/
│   ├── bug_report.yml            # Bug report form
│   ├── feature_request.yml       # Feature request form
│   └── config.yml                # Template configuration
├── dependabot.yml                # Automated dependency updates
├── labeler.yml                   # Auto-labeling rules
├── CODEOWNERS                    # Code ownership
├── pull_request_template.md      # PR template
└── BRANCH_PROTECTION.md          # Branch protection guide
```

---

## 🔄 Workflow Details

### 1. CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main`, `develop`
- Pull requests to `main`, `develop`
- Manual workflow dispatch

**Jobs:**

#### Lint (Code Quality)
- Black (code formatting)
- isort (import sorting)
- flake8 (style checking)
- mypy (type checking)
- pylint (code analysis)

#### Test
- **Matrix Strategy:**
  - OS: Ubuntu, macOS
  - Python: 3.11, 3.12, 3.13
- pytest with coverage
- Upload to Codecov
- **Coverage Threshold:** 80% minimum

#### Security
- Safety (vulnerability scan)
- Bandit (security linter)

#### Build
- Build Python package
- Validate with twine
- Upload artifacts

#### Integration
- Run integration tests (on main branch only)

**Status Check:**
- Final job that fails if any critical job fails
- Creates workflow summary

---

### 2. Release Pipeline (`release.yml`)

**Triggers:**
- Git tags matching `v*.*.*` (e.g., v1.0.0)
- Manual workflow dispatch

**Jobs:**

#### Validate Tag
- Verify semantic versioning format
- Extract version number

#### Build and Test
- Full test suite
- Coverage check
- Package build

#### Create Release
- Auto-generate changelog
- Create GitHub release
- Attach build artifacts

#### Publish to PyPI
- Automated PyPI publishing
- Uses trusted publishing (OIDC)

**Release Process:**
```bash
# Create a release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Pipeline automatically:
# 1. Validates version
# 2. Runs tests
# 3. Builds package
# 4. Creates GitHub release
# 5. Publishes to PyPI
```

---

### 3. Security Scanning (`security.yml`)

**Triggers:**
- Push to `main`, `develop`
- Pull requests to `main`
- Weekly schedule (Sunday midnight)
- Manual workflow dispatch

**Jobs:**

#### Dependency Scan
- Safety check (CVE database)
- pip-audit (PyPI advisories)

#### Code Security
- Bandit static analysis
- SARIF output for GitHub Security

#### Secret Scan
- TruffleHog secret detection
- Checks entire git history

#### License Check
- pip-licenses compliance
- Fails on GPL/AGPL licenses

#### Trivy Scan
- Filesystem vulnerability scan
- Uploads to GitHub Security tab

---

### 4. CodeQL Analysis (`codeql.yml`)

**Triggers:**
- Push to `main`, `develop`
- Pull requests to `main`
- Weekly schedule (Monday 6 AM)

**Analysis:**
- Python security vulnerabilities
- Code quality issues
- Security and quality queries
- Results in **Security** tab

---

### 5. Auto-Label PRs (`label-pr.yml`)

**Triggers:**
- PR opened, synchronized, reopened, edited

**Auto-Labels:**
- **By file changes:**
  - `code` - src/**/*.py
  - `tests` - tests/**/*.py
  - `documentation` - *.md, docs/
  - `ci/cd` - .github/workflows/
  - `dependencies` - requirements.txt, pyproject.toml
- **By size:**
  - `size/XS` - <10 lines
  - `size/S` - <100 lines
  - `size/M` - <500 lines
  - `size/L` - <1000 lines
  - `size/XL` - >1000 lines
- **By title keywords:**
  - `documentation` - "docs" in title
  - `tests` - "test" in title
  - `ci/cd` - "ci" or "workflow" in title

---

### 6. Auto-Merge (`auto-merge.yml`)

**Triggers:**
- PR labeled, synchronized, reviewed
- Check suite completed

**Behavior:**
- **Dependabot PRs:** Auto-approve minor/patch updates
- **With `automerge` label:**
  - Auto-merge when all checks pass
  - Requires approval
  - Uses squash merge
- **Safety checks:**
  - Must pass all CI checks
  - Must have required approvals
  - Cannot have "do not merge" label

---

### 7. Dependency Review (`dependency-review.yml`)

**Triggers:**
- Pull requests to `main`

**Checks:**
- New dependency vulnerabilities
- License compliance
- Fails on moderate+ severity
- Comments on PR with findings

---

## 🔐 Security Features

### Automated Security Scanning

1. **CodeQL (Weekly + PR)**
   - Advanced semantic code analysis
   - Detects security vulnerabilities
   - Results in Security tab

2. **Dependabot (Weekly)**
   - Automated dependency updates
   - Security patch notifications
   - Auto-PRs for updates

3. **Bandit (Every CI run)**
   - Python security linting
   - Checks for common vulnerabilities

4. **Safety (Every CI run)**
   - CVE database checks
   - Known vulnerability detection

5. **Secret Scanning (PR + Weekly)**
   - TruffleHog detection
   - Prevents credential leaks

6. **Trivy (Weekly)**
   - Filesystem vulnerability scan
   - SARIF upload to GitHub

---

## 📊 Quality Gates

All PRs must pass:

### Required Checks
- ✅ Code formatting (Black, isort)
- ✅ Linting (flake8, pylint)
- ✅ Type checking (mypy)
- ✅ Unit tests (pytest)
- ✅ Code coverage (≥80%)
- ✅ Security scan (Bandit)
- ✅ Dependency check
- ✅ Build validation

### Optional but Recommended
- Code review approval
- Integration tests
- Performance benchmarks

---

## 🏷️ Labels

### Automatic Labels
- `bug` - Bug reports
- `enhancement` - Feature requests
- `documentation` - Doc changes
- `dependencies` - Dependency updates
- `tests` - Test changes
- `ci/cd` - CI/CD changes
- `size/*` - PR size indicators

### Manual Labels
- `needs-triage` - Needs review
- `good first issue` - Good for newcomers
- `help wanted` - Community help needed
- `wontfix` - Will not be implemented
- `duplicate` - Duplicate issue
- `invalid` - Invalid issue
- `question` - Question, not issue
- `automerge` - Auto-merge when approved
- `do not merge` - Blocks auto-merge

---

## 🚀 Release Process

### Semantic Versioning

We follow [Semantic Versioning 2.0.0](https://semver.org/):
- **MAJOR** (v1.0.0): Breaking changes
- **MINOR** (v0.1.0): New features (backwards compatible)
- **PATCH** (v0.0.1): Bug fixes (backwards compatible)

### Creating a Release

**Option 1: Git Tag**
```bash
# Create and push tag
git tag -a v1.2.0 -m "Release v1.2.0: Add new feature"
git push origin v1.2.0

# Pipeline automatically handles the rest
```

**Option 2: GitHub UI**
1. Go to **Releases** → **Draft a new release**
2. Create new tag (e.g., `v1.2.0`)
3. Auto-generate release notes
4. Publish release
5. Pipeline runs automatically

**Option 3: Workflow Dispatch**
1. Go to **Actions** → **Release**
2. Click **Run workflow**
3. Enter version (e.g., `v1.2.0`)
4. Run workflow

### What Happens
1. ✅ Tag validated (semantic versioning)
2. ✅ Full test suite runs
3. ✅ Package built
4. ✅ Changelog generated from PRs
5. ✅ GitHub release created
6. ✅ Package published to PyPI
7. ✅ Artifacts uploaded

---

## 📝 Issue & PR Templates

### Bug Reports
- Structured form with required fields
- Environment information
- Reproduction steps
- Expected vs actual behavior
- Logs and screenshots

### Feature Requests
- Problem statement
- Proposed solution
- Use cases
- Priority level
- Alternative considerations

### Pull Requests
- Type of change
- Related issues
- Changes made
- Testing performed
- Comprehensive checklist

---

## 👥 Code Ownership

See [CODEOWNERS](.github/CODEOWNERS) for details.

**Key areas:**
- `/src/sbom_fetcher/domain/` - Critical business logic
- `/src/sbom_fetcher/infrastructure/` - Infrastructure code
- `.github/workflows/` - CI/CD configuration
- `/tests/` - Test suite

**Reviews required for:**
- All source code changes
- Test modifications
- CI/CD updates
- Documentation updates

---

## 🛡️ Branch Protection

See [BRANCH_PROTECTION.md](.github/BRANCH_PROTECTION.md) for full details.

### Main Branch
- ✅ Requires PR with 1 approval
- ✅ Requires all CI checks to pass
- ✅ Requires Code Owner review
- ✅ Requires signed commits
- ✅ Requires linear history
- ✅ No direct pushes

### Recommended Setup
```bash
# Enable branch protection
gh api repos/tedg-dev/GitHub-SBOM-fetcher/branches/main/protection \
  --method PUT \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_status_checks[strict]=true \
  --field enforce_admins=true
```

---

## 📈 Monitoring & Metrics

### Where to Check Status

**1. Actions Tab**
- All workflow runs
- Success/failure rates
- Execution times

**2. Security Tab**
- CodeQL findings
- Dependabot alerts
- Secret scanning results
- Trivy vulnerabilities

**3. Insights**
- Code frequency
- Commit activity
- Contributors
- Dependency graph

**4. Pull Requests**
- Check status
- Review status
- Labels applied

---

## 🔧 Troubleshooting

### CI Failure

**Lint Failures:**
```bash
# Fix locally
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

**Test Failures:**
```bash
# Run tests locally
pytest tests/ -v --cov=sbom_fetcher
```

**Coverage Too Low:**
```bash
# Check coverage
coverage report --fail-under=80
coverage html
open htmlcov/index.html
```

### Release Failures

**Invalid Tag:**
- Must match `v*.*.*` format
- Example: `v1.2.3`

**Test Failures:**
- All tests must pass before release
- Fix issues, create new tag

**PyPI Publish Failure:**
- Check PyPI credentials (uses OIDC)
- Verify package version doesn't exist
- Check package metadata

---

## 🎓 Best Practices

### For Contributors

1. **Before Creating PR:**
   - Run linters locally
   - Run full test suite
   - Update documentation
   - Add tests for new features

2. **PR Guidelines:**
   - Use descriptive titles
   - Link related issues
   - Fill out template completely
   - Request reviews

3. **During Review:**
   - Respond to feedback promptly
   - Keep PRs focused and small
   - Update based on review comments

### For Maintainers

1. **Code Review:**
   - Check test coverage
   - Verify documentation
   - Test locally if needed
   - Approve only when satisfied

2. **Releases:**
   - Review changelog
   - Test release candidates
   - Follow semantic versioning
   - Document breaking changes

3. **Security:**
   - Monitor Dependabot PRs
   - Review security alerts weekly
   - Keep dependencies updated

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Dependabot Documentation](https://docs.github.com/en/code-security/dependabot)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Branch Protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [Code Owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)

---

## 🚀 Quick Start for New Contributors

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/YOUR-USERNAME/GitHub-SBOM-fetcher.git
   cd GitHub-SBOM-fetcher
   ```
3. **Set up environment**
   ```bash
   ./setup_environment.sh
   ```
4. **Create a branch**
   ```bash
   git checkout -b feature/my-feature
   ```
5. **Make changes and test**
   ```bash
   pytest tests/ -v
   black src/ tests/
   ```
6. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```
7. **Wait for CI checks** ✅

---

**Status:** ✅ Production Ready  
**Last Updated:** 2025-12-05  
**Maintainer:** @tedg-dev
