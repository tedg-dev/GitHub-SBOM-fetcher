# Releasing SBOM Fetcher

This document describes the versioning and release process for SBOM Fetcher.

## Versioning Strategy

This project uses **Semantic Versioning (SemVer)**: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes that require users to modify their code
- **MINOR**: New features that are backwards-compatible
- **PATCH**: **Automatically incremented** on every merged PR

### Automatic Version Bumping

The **PATCH version is automatically incremented** every time a PR is merged to `main`. This is handled by the `version-bump.yml` workflow.

**Example:** If the current version is `2.0.22` and a PR is merged, the version becomes `2.0.23`.

### Version File

The single source of truth for the version is the `VERSION` file in the project root. This file contains only the version number (e.g., `2.0.22`).

The version is automatically read by:
- `pyproject.toml` via dynamic versioning
- `sbom_fetcher/__init__.py` for runtime access via `sbom_fetcher.__version__`

## Automatic Version Updates

When a PR is merged to `main`:
1. The `version-bump.yml` workflow triggers automatically
2. The PATCH version is incremented (e.g., `2.0.22` → `2.0.23`)
3. The change is committed directly to `main` with `[skip ci]` to avoid loops
4. No manual intervention required for PATCH bumps

## Manual Version Updates (MAJOR/MINOR)

For **MAJOR** or **MINOR** version changes, update manually:

1. Update the `VERSION` file:
   ```bash
   echo "2.1.0" > VERSION   # For minor bump
   echo "3.0.0" > VERSION   # For major bump
   ```

2. Create a PR for the version change:
   ```bash
   git checkout -b release/v2.1.0
   git add VERSION
   git commit -m "chore: bump version to 2.1.0"
   git push -u origin release/v2.1.0
   gh pr create --title "Release v2.1.0" --body "Version bump for release 2.1.0"
   ```

3. Merge the PR (this will NOT trigger another auto-bump since the bump workflow detects manual changes)

## Creating a Release

### Prerequisites

1. Ensure all changes are merged to `main` via Pull Requests
2. Ensure CI/CD pipeline passes on `main`
3. Ensure code coverage is at 97%+ (minimum 95%)

### Step 2: Create Release Tag

After the version bump PR is merged:

```bash
git checkout main
git pull origin main
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin v2.1.0
```

**Important**: Use annotated tags (`-a` flag) for releases.

### Step 3: Automated Release

Pushing a tag matching `v*.*.*` triggers the release workflow which:

1. **Validates** the semantic version format
2. **Runs** the full test suite with coverage checks
3. **Builds** the Python package (wheel and sdist)
4. **Generates SBOMs** in both formats:
   - SPDX JSON (`sbom-spdx-v2.1.0.json`)
   - CycloneDX JSON (`sbom-cyclonedx-v2.1.0.json`)
5. **Creates** a GitHub Release with:
   - Auto-generated changelog
   - Package artifacts (`.tar.gz`, `.whl`)
   - SBOM files
6. **Publishes** to PyPI (if configured)

### Manual Release Trigger

You can also trigger a release manually via GitHub Actions:

1. Go to Actions → Release workflow
2. Click "Run workflow"
3. Enter the version (e.g., `v2.1.0`)
4. Click "Run workflow"

## SBOM Generation

Each release automatically generates Software Bill of Materials (SBOM) files using [Syft](https://github.com/anchore/syft):

| Format | File | Standard |
|--------|------|----------|
| SPDX | `sbom-spdx-v{version}.json` | [SPDX 2.3](https://spdx.github.io/spdx-spec/) |
| CycloneDX | `sbom-cyclonedx-v{version}.json` | [CycloneDX 1.4](https://cyclonedx.org/) |

### SBOM Contents

The generated SBOMs include:
- **Component Version String**: Exact version from the `VERSION` file
- **Dependencies**: All Python dependencies with versions
- **License Information**: MIT license for this project
- **Package Metadata**: Name, author, description

### Local SBOM Generation

To generate SBOMs locally (requires Syft installed):

```bash
# Install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin

# Generate SPDX format
syft dir:. --output spdx-json=sbom-spdx.json --source-name "sbom-fetcher" --source-version "$(cat VERSION)"

# Generate CycloneDX format
syft dir:. --output cyclonedx-json=sbom-cyclonedx.json --source-name "sbom-fetcher" --source-version "$(cat VERSION)"
```

## Pre-release Versions

For pre-release versions, use the following formats:
- Alpha: `v2.1.0-alpha.1`
- Beta: `v2.1.0-beta.1`
- Release Candidate: `v2.1.0-rc.1`

Pre-releases are automatically marked as such in GitHub Releases.

## Checking the Current Version

```python
import sbom_fetcher
print(sbom_fetcher.__version__)
```

Or from the command line:
```bash
cat VERSION
```

## Release Checklist

- [ ] All PRs merged to `main`
- [ ] CI/CD passes on `main`
- [ ] Coverage ≥ 97%
- [ ] `VERSION` file updated
- [ ] Version bump committed and merged
- [ ] Annotated tag created and pushed
- [ ] Release workflow completed successfully
- [ ] GitHub Release created with artifacts
- [ ] SBOM files attached to release
- [ ] PyPI package published (if applicable)

## Troubleshooting

### Release Workflow Fails

1. Check the workflow logs in GitHub Actions
2. Common issues:
   - Invalid version format (must be `v#.#.#`)
   - Test failures
   - Coverage below threshold

### Version Mismatch

If the version in different places doesn't match:
1. The `VERSION` file is the source of truth
2. Rebuild the package: `python -m build`
3. Reinstall: `pip install -e .`

### SBOM Generation Issues

If Syft fails:
1. Check Syft is installed correctly
2. Verify the source directory structure
3. Check for file permission issues
