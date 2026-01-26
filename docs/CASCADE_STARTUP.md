# Cascade/Windsurf Startup Notes — GitHub SBOM Fetcher

**Repository root:** `/Users/tedg/workspace/fetch_sbom`

This document is intended to be the first thing to open when returning to this repo in Windsurf/Cascade.

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

- Run as module:
  - `python -m sbom_fetcher --gh-user OWNER --gh-repo REPO --account ACCOUNT [--debug]`
- Run installed script (from `pyproject.toml`):
  - `sbom-fetcher --gh-user OWNER --gh-repo REPO --account ACCOUNT [--debug]`

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

Observed state (per `tests/TEST_STATUS.md`):

- 60 tests total (39 passing, 21 failing/errors)
- Coverage reported around 29%

Coverage threshold is **97%** across all configs:

- `pytest.ini`: `--cov-fail-under=97`
- `pyproject.toml`: `--cov-fail-under=97`
- `.github/workflows/ci.yml`: `--fail-under=97`
- `.github/workflows/release.yml`: `--fail-under=97`

## Operational rules (human process)

### Rule: PR-first workflow

- Do not commit directly to `main`.
- Work on a feature branch and merge via PR.

### Rule: Version bump workflow

- PATCH bumps are triggered automatically on PR merge (via `version-bump.yml`).
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

### Rule: Releases

- Create an annotated tag `vX.Y.Z` on `main` to trigger release workflow.

### Rule: Secrets

- Never commit `keys.json`.
- Prefer fine-grained PATs where possible; ensure required permissions for dependency graph access.

## Meta-rule (NEW): record new rules here

**Any time a new rule/process requirement is introduced (CI, release, branching, coverage, security, etc.), it must be added to the “Operational rules” section of this document (or a clearly-labeled new section) in the same PR.**

Rationale: this file is the persistent “startup memory” for returning to the repo.

## What to open first next time

- `docs/CASCADE_STARTUP.md` (this file)
- `README.md`
- `src/sbom_fetcher/application/main.py`
- `src/sbom_fetcher/services/sbom_service.py`
- `.github/workflows/ci.yml` and `version-bump.yml`

