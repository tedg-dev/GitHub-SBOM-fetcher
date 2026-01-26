# Cascade/Windsurf Startup Notes — GitHub SBOM Fetcher

**Repository root:** `/Users/tedg/workspace/fetch_sbom`

This document is intended to be the first thing to open when returning to this repo in Windsurf/Cascade.

---

## ⚠️ FIRST ACTIONS ON EVERY STARTUP

**Before doing ANY work, run the setup script:**
```bash
./setup_environment.sh
```

This is **MANDATORY**. The script:
- Sets up the Python virtual environment
- Installs all dependencies
- Verifies the installation
- Shows current VERSION

**Critical environment notes:**
- Use `python3`, NOT `python` (pyenv environment may not have `python` alias)
- After setup, activate venv: `source venv/bin/activate`
- Run tests with: `python3 -m pytest tests/ -v`

---

## Purpose (what this repo/product does)

SBOM Fetcher is a Python tool that:

1. Fetches a **root** SBOM from the GitHub Dependency Graph SBOM API (SPDX JSON).
2. Parses the SBOM to extract dependency packages (via PURLs).
3. Maps each dependency package to a likely **GitHub repository** (npm/PyPI/RubyGems metadata + GitHub search fallbacks).
4. Deduplicates by repository (downloads each repo once, even if multiple versions appear in the dependency tree).
5. Fetches SBOMs for each unique dependency repository.
6. Writes output artifacts (SBOM JSONs + version mapping + a Markdown execution report).

Key limitation: GitHub’s SBOM endpoint represents the **current default branch state**, not historical versions. Deduplication is intentional and recorded in `version_mapping.json`.

## Quick Start (how to run)

```bash
# Always use python3, not python
python3 -m sbom_fetcher --gh-user OWNER --gh-repo REPO --account ACCOUNT [--debug]

# Or via installed script
sbom-fetcher --gh-user OWNER --gh-repo REPO --account ACCOUNT [--debug]
```

## Credentials / keys.json formats

Runtime token loading is in `src/sbom_fetcher/application/main.py:load_token()`.

Supported formats:

1. **Multi-account (recommended):**

```json
{
  "accounts": [
    {"username": "your-personal", "token": "ghp_..."},
    {"username": "your-work", "token": "ghp_..."}
  ]
}
```

2. **Legacy single-token formats (backward compatible):**

```json
{"github_token": "ghp_..."}
```

```json
{"token": "ghp_..."}
```

Notes:

- CLI requires `--account` (see `src/sbom_fetcher/application/cli.py`).
- `setup_environment.sh` prints a simplified `keys.json` format; runtime supports more.

## Output structure

Outputs go under `sboms/` by default:

```
sboms/
  sbom_export_<timestamp>/
    <owner>_<repo>/
      <owner>_<repo>_root.json
      <owner>_<repo>_execution_report.md
      version_mapping.json
      dependencies/
        <dep_owner>_<dep_repo>_<default_branch>.json
```

## Architecture (where to look)

### Entry points

- `src/sbom_fetcher/__main__.py`
  - `python -m sbom_fetcher`
- `src/sbom_fetcher/application/main.py`
  - Dependency injection / wiring
  - Token loading
  - Constructs service objects
- `src/sbom_fetcher/application/cli.py`
  - CLI args: `--gh-user`, `--gh-repo`, `--account`, `--key-file`, `--output-dir`, `--debug`
  - Logging: writes to `docs/logs/run_<timestamp>.log`

### Core orchestration

- `src/sbom_fetcher/services/sbom_service.py`
  - Implements the primary workflow:
    - fetch root SBOM
    - parse packages
    - map to GitHub repos
    - dedupe by repo
    - download dependency SBOMs
    - write `version_mapping.json`
    - generate Markdown report

### GitHub API interaction

- `src/sbom_fetcher/services/github_client.py`
  - Root SBOM fetch: `GET /repos/{owner}/{repo}/dependency-graph/sbom`
  - Dependency SBOM downloads: same endpoint per mapped repo
  - Default branch lookup: `GET /repos/{owner}/{repo}`
  - Retry logic and error classification:
    - `404` → permanent (dependency graph not enabled)
    - `403` → permanent
    - `429` → transient
    - `5xx` → transient with retries

### Parsing

- `src/sbom_fetcher/services/parsers.py`
  - `PURLParser` parses `pkg:<ecosystem>/<name>@<version>`
  - `SBOMParser.extract_packages()` expects SPDX-style `packages` list and reads PURLs from `externalRefs`.

### Package → GitHub mapping

- `src/sbom_fetcher/services/mappers.py`
  - Ecosystems supported:
    - npm (`NPMPackageMapper`)
    - PyPI (`PyPIPackageMapper`)
    - RubyGems (`RubyGemsMapper`)
    - GitHub Actions (`GitHubActionsMapper`)
  - Fallbacks:
    - `search_github_for_package()` (GitHub repo search, uses token if provided)
    - `search_org_for_package()` (search within root org, for internal packages)

- `src/sbom_fetcher/services/mapper_factory.py`
  - Selects mapper per ecosystem and applies org-search fallback.

### Reporting

- `src/sbom_fetcher/services/reporters.py`
  - Produces `<owner>_<repo>_execution_report.md`.
  - Separates failures into **permanent** vs **transient**.
  - Includes a section describing why unmapped packages occur.

### Domain model and error types

- `src/sbom_fetcher/domain/models.py`
  - `PackageDependency`, `GitHubRepository`, `FetcherStats`, `FetcherResult`, etc.
- `src/sbom_fetcher/domain/exceptions.py`
  - Custom exception hierarchy; includes `ErrorType` usage.

### Infrastructure

- `src/sbom_fetcher/infrastructure/config.py`
  - Config defaults + env var overrides.
- `src/sbom_fetcher/infrastructure/http_client.py`
  - HTTP abstraction + mock client for tests.
- `src/sbom_fetcher/infrastructure/filesystem.py`
  - Repository pattern helpers for writing files (note: main service writes many files directly today).

## GitHub automation (workflows)

Workflows live in `.github/workflows/`:

- `ci.yml`
  - Lint (black/isort/flake8/mypy/pylint)
  - Tests matrix: ubuntu + macOS, Python 3.11/3.12/3.13
  - Build (python -m build + twine check)
  - Integration tests
  - Status-check aggregator job

- `security.yml`
  - Safety + pip-audit
  - Bandit
  - Trufflehog (secrets)
  - License check (deny GPL/AGPL)
  - Trivy

- `codeql.yml`
  - CodeQL analysis (security-and-quality)

- `dependency-review.yml`
  - Blocks moderate+ severity and denies GPL/AGPL licenses on PRs

- `label-pr.yml` and `.github/labeler.yml`
  - Auto-label PRs by touched files + PR size

- `auto-merge.yml`
  - Auto-merge Dependabot PRs; auto-merge PRs with `automerge` label if mergeable

- `release.yml`
  - Trigger: tag `v*.*.*` or workflow_dispatch
  - Runs tests/build
  - Generates SBOMs for the package itself using Syft (SPDX + CycloneDX)
  - Creates GitHub Release + attaches artifacts
  - Publishes to PyPI only if repo is `tedg-dev/GitHub-SBOM-fetcher`

- `version-bump.yml`
  - Trigger: PR closed on `main` AND merged (skips if branch starts with `version-bump/` or title contains `bump version`)
  - Bumps PATCH in `VERSION`, creates branch `version-bump/X.Y.Z`, and attempts to open a PR
  - **Note:** GITHUB_TOKEN may lack permission to create PRs; see "Cascade automation" rule below

## Versioning and releases

- Version is stored in `VERSION` and read dynamically by `pyproject.toml`.
- Policy (as documented in `RELEASING.md`):
  - PATCH: auto-bumped on each PR merge
  - MINOR/MAJOR: manual via PR modifying `VERSION`
  - Releases: annotated tag `vX.Y.Z` triggers `release.yml`

## Tests and coverage (current state in this folder)

Tests are under `tests/` and include unit + integration structure.

Important docs:

- `tests/README.md`
- `tests/TEST_STATUS.md`
- `docs/CODE_COVERAGE_REQUIREMENTS.md`

Coverage threshold is **97%** across all configs:

- `pytest.ini`: `--cov-fail-under=97`
- `pyproject.toml`: `--cov-fail-under=97`
- `.github/workflows/ci.yml`: `--fail-under=97`
- `.github/workflows/release.yml`: `--fail-under=97`

## Operational rules (Cascade process)

### Rule: PR-first workflow

- **Never** commit directly to `main`.
- Always work on a feature branch and merge via PR.
- Cascade chooses branch names (user has delegated this).
- Use conventional prefixes: `fix/`, `feat/`, `chore/`, `docs/`, `test/`

### Rule: Version bump workflow

- PATCH bumps are triggered automatically on PR merge (via `version-bump.yml`).
- **Version bumps only occur for code changes** — documentation-only PRs do NOT bump the version.
- The workflow skips bumping if:
  - PR title starts with `docs:`
  - PR has the `documentation` label
  - PR is a version-bump PR itself
- The workflow creates a `version-bump/X.Y.Z` branch and attempts to open a PR.
- If the workflow fails to create the PR (GITHUB_TOKEN permission), Cascade should create it:
  ```bash
  gh pr create --head version-bump/X.Y.Z --base main --title "chore: bump version to X.Y.Z" --body "Automated patch bump"
  gh pr merge <PR#> --squash
  ```
- Do not manually bump PATCH unless you are intentionally overriding automation.

### Rule: Cascade automation for version bumps

After merging any PR to `main`, check if `version-bump.yml` succeeded:
```bash
gh run list --workflow=version-bump.yml --limit 1
```
If it failed and a `version-bump/*` branch exists on origin, create and merge the PR using `gh` CLI (see above).

### Rule: Consolidated PR workflow (minimize prompts)

**For code changes (will trigger version bump):**
```bash
# 1. Create branch, commit, push, create PR (ONE command)
git checkout -b <branch> && git add -A && git commit -m "<message>" && git push -u origin <branch> && gh pr create --title "<title>" --body "<body>"

# 2. Merge PR
gh pr merge <PR#> --squash

# 3. After merge: pull, create version-bump PR, merge it, cleanup (ONE command)
git checkout main && git pull --ff-only && git fetch && \
  BUMP_BRANCH=$(git branch -r | grep 'version-bump/' | tail -1 | xargs | sed 's|origin/||') && \
  gh pr create --head "$BUMP_BRANCH" --base main --title "chore: bump version" --body "Auto bump" && \
  gh pr merge "$BUMP_BRANCH" --squash && \
  git pull --ff-only && git branch -d <branch> 2>/dev/null; \
  git push origin --delete <branch> "$BUMP_BRANCH" 2>/dev/null || true
```

**For docs-only changes (no version bump):**
```bash
# 1. Create branch, commit, push, create PR
git checkout -b docs/<name> && git add -A && git commit -m "docs: <message>" && git push -u origin docs/<name> && gh pr create --title "docs: <title>" --body "<body>"

# 2. Merge and cleanup
gh pr merge <PR#> --squash && git checkout main && git pull --ff-only && git branch -d docs/<name> 2>/dev/null; git push origin --delete docs/<name> 2>/dev/null || true
```

### Rule: Releases

- Create an annotated tag `vX.Y.Z` on `main` to trigger release workflow.

### Rule: Secrets

- Never commit `keys.json`.
- Prefer fine-grained PATs where possible; ensure required permissions for dependency graph access.

---

## Cascade-specific rules (learned behaviors)

### Rule: Command execution

- **Never run `cd` commands** — use `Cwd` parameter instead
- **Sequential git commands** — always wait for `git add` to complete before `git commit`
- **Avoid parallel git operations** — git commands that modify state should run sequentially
- **Use `python3`** — never use bare `python` (may not exist in pyenv)

### Rule: Naming conventions

- Cascade is authorized to choose branch names without asking
- Use descriptive, conventional branch names:
  - `fix/descriptive-issue`
  - `feat/new-feature`
  - `chore/maintenance-task`
  - `docs/update-documentation`
  - `version-bump/X.Y.Z` (for version bumps only)

### Rule: User interaction

- Do not prompt user unless there is a **real choice** to be made
- If multiple valid options exist, present them and ask
- If there's an industry-standard approach, use it without asking
- Proceed autonomously on routine operations (branch names, merge strategy, cleanup)

### Rule: Testing before PR

- Run tests before creating PRs when code changes are involved:
  ```bash
  source venv/bin/activate && python3 -m pytest tests/ -v --cov
  ```
- Coverage must meet 97% threshold

### Rule: Fix pre-existing failures

- **All pre-existing lint failures must be corrected** — do not leave or ignore them
- **All pre-existing test failures must be corrected** — failing tests block CI
- When encountering failures, fix the root cause rather than disabling or skipping
- If a fix is non-trivial, create a dedicated PR to address it before other work

---

## Meta-rule: record new rules here

**Any time a new rule/process requirement is introduced (CI, release, branching, coverage, security, etc.), it must be added to the “Operational rules” section of this document (or a clearly-labeled new section) in the same PR.**

Rationale: this file is the persistent “startup memory” for returning to the repo.

## What to open/do first next time

1. **Read this file** (`docs/CASCADE_STARTUP.md`)
2. **Run setup**: `./setup_environment.sh`
3. **Check VERSION**: `cat VERSION`
4. **Check for pending version-bump branches**: `git fetch && git branch -r | grep version-bump`

Key files for context:
- `README.md` — user-facing documentation
- `src/sbom_fetcher/application/main.py` — entry point and DI wiring
- `src/sbom_fetcher/services/sbom_service.py` — core workflow orchestration
- `.github/workflows/version-bump.yml` — understand the automation

