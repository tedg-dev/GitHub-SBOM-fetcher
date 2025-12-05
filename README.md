# GitHub SBOM API Fetcher

**Automated tool for collecting Software Bill of Materials (SBOM) from GitHub repositories and their dependencies**

Uses GitHub's official SBOM API and package registry APIs for comprehensive, maintainable dependency discovery and SBOM collection.

---

## Features

✅ **Complete Dependency Discovery** - Fetches full dependency trees from GitHub's SBOM API  
✅ **Smart Package Mapping** - Uses npm/PyPI registry APIs to map packages to GitHub repos  
✅ **Intelligent Deduplication** - Downloads each repository once, tracks version relationships  
✅ **Private Repository Support** - Works with repositories requiring authentication  
✅ **Diagnostic Reporting** - Detailed execution reports with mapping diagnostics  
✅ **Production Ready** - Modular architecture, comprehensive error handling  

---

## Quick Start

```bash
# Install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure (create keys.json with your GitHub token)
cp key.sample.json keys.json
# Edit keys.json with your token

# Run
python -m sbom_fetcher --gh-user OWNER --gh-repo REPO

# With diagnostic logging
python -m sbom_fetcher --gh-user OWNER --gh-repo REPO --debug
```

---

## How It Works

### 1. Fetch Root SBOM
Retrieves the SBOM for your target repository using GitHub's Dependency Graph API:
```
GET /repos/{owner}/{repo}/dependency-graph/sbom
```

### 2. Extract Dependencies
Parses the SBOM (SPDX 2.3 format) to extract all packages:
- Package names, versions, ecosystems (npm, PyPI, etc.)
- Package URLs (purls): `pkg:npm/lodash@4.17.5`

### 3. Map Packages to GitHub Repositories
Queries package registries to find authoritative repository URLs:

**For npm packages:**
```
GET https://registry.npmjs.org/{package-name}
→ Extract "repository" field
→ Validate GitHub URL and extract owner/repo
```

**For PyPI packages:**
```
GET https://pypi.org/pypi/{package-name}/json
→ Extract project_urls["Source"] or "Homepage"
→ Validate GitHub URL and extract owner/repo
```

**Diagnostic Logging:**
- ✅ Successfully mapped: `pkg:npm/lodash → lodash/lodash`
- ❌ Mapping failed: Shows exact reason (no repository field, non-GitHub URL, etc.)

### 4. Deduplicate Repositories
Groups packages by repository to avoid duplicate downloads:
- Multiple versions of `lodash` → single download from `lodash/lodash`
- Tracks version relationships in `version_mapping.json`
- Saves 50%+ storage, reduces download time

### 5. Download Dependency SBOMs
Fetches SBOM for each unique repository:
```
GET /repos/{owner}/{repo}/dependency-graph/sbom
```

Handles:
- Rate limiting with automatic delays
- Failed downloads (dep graph not enabled, HTTP errors)
- Branch name discovery (main vs master)

### 6. Generate Reports
Creates comprehensive execution report showing:
- Statistics (mapped packages, unique repos, duplicates)
- Failed downloads with reasons
- **Unmapped packages with diagnostic information**:
  - Why mapping failed (npm metadata missing, non-GitHub repo, etc.)
  - Package registry query URLs
  - Registry responses
  - Explanation that some packages may have repos but lack registry metadata

---

## Output Structure

```
sboms/
  sbom_export_2025-12-05_09.19.04/
    tedg-dev_beatBot/
      # Root SBOM
      tedg-dev_beatBot_root.json
      
      # Execution report with diagnostics
      tedg-dev_beatBot_execution_report.md
      
      # Version tracking
      version_mapping.json
      
      # Dependency SBOMs
      dependencies/
        lodash_lodash_main.json
        caolan_async_master.json
        ...
```

### Example Output

```
======================================================================
STEP 1: Fetching Root SBOM
======================================================================
✅ Root SBOM fetched successfully

======================================================================
STEP 2: Parsing Dependency Packages
======================================================================
Found 229 valid packages in SBOM

======================================================================
STEP 3: Mapping Packages to GitHub Repositories
======================================================================
Mapped 222 packages to GitHub repos
Packages without GitHub repos: 7

Unmapped packages:
  - boolbase (npm) v1.0.0
  - eyes (npm) v0.1.8
  - @ffmpeg-installer/darwin-x64 (npm) v4.0.4
  ...

======================================================================
STEP 4: Downloading Dependency SBOMs (Deduplicated)
======================================================================
Total packages: 222
Unique repositories: 166
Duplicates to skip: 56

[1/166] Fetching SBOM for lodash/lodash (versions: 3.10.1, 4.17.5, ...)
[2/166] Fetching SBOM for caolan/async (versions: 0.1.22, 2.6.0, ...)
...

======================================================================
SUMMARY
======================================================================
Root SBOM dependency repositories: 229
Mapped to GitHub repos: 222
Unique repositories: 166
Duplicate versions skipped: 56
Packages without GitHub repos: 7

SBOMs downloaded successfully: 164
SBOMs failed (permanent): 2
Elapsed time: 4m 20s
```

---

## Understanding Package Mapping

### Why Some Packages Don't Map

The tool relies on **package registry metadata** to discover GitHub repositories:

1. **Query registry**: `https://registry.npmjs.org/boolbase`
2. **Extract repository**: Look for `"repository"` field
3. **Validate**: Verify it's a GitHub URL
4. **Map**: Extract owner/repo

**Packages fail to map when:**
- npm/PyPI metadata has `"repository": null`
- Old/unmaintained packages (published before repository fields were standard)
- Platform-specific binaries (no source code to link)
- Publisher oversight (maintainer didn't include repository metadata)

**Important:** Some unmapped packages DO have GitHub repositories, but the package registry doesn't link to them. Without this metadata, the tool cannot discover the repository location.

**Example:**
- `boolbase` has a GitHub repo: https://github.com/fb55/boolbase
- But npm metadata has: `"repository": null`
- **Result**: Cannot map (registry doesn't provide repository location)

### Diagnostic Report

The execution report includes a detailed "Packages That Could Not Be Mapped to GitHub" section showing:

- **How mapping works** (4-step process)
- **Why mapping fails** (common reasons)
- **Per-package diagnostics**:
  - Registry query URL
  - Registry response
  - Result explanation
- **Solutions**: Contact maintainer, use alternative tools, manual fetch

**This transparency helps distinguish:**
- Packages with no GitHub repos (correctly unmapped)
- Packages with repos but missing registry metadata (limitation in package metadata)

---

## Configuration

### GitHub Token

Create `keys.json` in the project root:

**Format:**
```json
{
  "username": "your-github-username",
  "token": "ghp_yourPersonalAccessToken"
}
```

**Token Requirements:**
- **Classic PAT**: Include `repo` scope for private repos
- **Fine-grained PAT**: Repository permissions:
  - Contents (Read)
  - Dependency graph (Read)

**Security:**
- Use `key.sample.json` as template
- Never commit `keys.json` (already in `.gitignore`)
- Rotate tokens regularly

---

## Command-Line Options

```bash
python -m sbom_fetcher [OPTIONS]
```

**Required:**
```
--gh-user USER    Repository owner
--gh-repo REPO    Repository name
```

**Optional:**
```
--key-file FILE      Path to keys.json (default: keys.json)
--output-dir DIR     Output directory (default: sboms)
--debug              Enable diagnostic logging
```

**Examples:**
```bash
# Basic
python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot

# With diagnostics
python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --debug

# Custom output
python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --output-dir ./my_sboms
```

---

## Architecture

### Modular Design

```
src/sbom_fetcher/
  domain/
    models.py              # Core data structures
  
  services/
    github_client.py       # GitHub API interactions
    parsers.py             # SBOM parsing
    mappers.py             # Package → GitHub mapping
    mapper_factory.py      # Ecosystem-specific mappers
    sbom_service.py        # Main orchestration
    reporters.py           # Report generation
  
  infrastructure/
    config.py              # Configuration management
    repository.py          # File system operations
```

### Key Components

**1. GitHub Client** (`github_client.py`)
- Fetches SBOMs from GitHub API
- Handles authentication, rate limiting
- Discovers default branch names (main/master)
- Caches API responses

**2. Package Mappers** (`mappers.py`, `mapper_factory.py`)
- NPM: Queries npm registry API
- PyPI: Queries PyPI JSON API
- URL encoding for scoped packages (`@org/pkg`)
- Handles multiple repository field formats
- **Diagnostic logging** at every decision point

**3. SBOM Service** (`sbom_service.py`)
- Orchestrates the 6-step workflow
- Tracks unmapped packages with reasons
- Handles deduplication
- Generates comprehensive statistics

**4. Reporters** (`reporters.py`)
- Markdown execution reports
- **Detailed diagnostic sections**:
  - How mapping works
  - Why packages failed to map
  - Per-package registry queries and responses
  - Solutions and alternatives

---

## Troubleshooting

### Debug Mode

Enable detailed logging to diagnose issues:
```bash
python -m sbom_fetcher --gh-user OWNER --gh-repo REPO --debug
```

**Shows:**
- npm/PyPI registry queries and responses
- Package mapping decisions
- Why each package succeeded or failed
- GitHub API interactions

### Common Issues

**"Failed to load GitHub token"**
- Ensure `keys.json` exists and is valid JSON
- Check file permissions

**403 Forbidden**
- Verify token has correct permissions
- Check token hasn't expired

**404 Not Found - Repository**
- Verify repository exists
- For private repos, ensure token grants access

**"Dependency graph not enabled"**
- GitHub's dependency graph must be enabled
- Check: `https://github.com/{owner}/{repo}/network/dependencies`

**Packages Without GitHub Repositories**
- Normal for platform-specific binaries
- Check execution report for diagnostic details
- Some may have repos but lack registry metadata

### Understanding Unmapped Packages

The execution report shows **exactly why** each package failed to map:

```markdown
#### boolbase (v1.0.0)
- **Package Registry Query:** `https://registry.npmjs.org/boolbase`
- **Registry Response:** Package metadata contains `"repository": null`
- **Result:** ❌ Cannot determine GitHub repository location from package metadata

**Important**: This package may have a GitHub repository, but the npm
registry metadata does not link to it.
```

**Solutions:**
1. Contact package maintainer to add repository field
2. Use alternative SBOM tools (syft, grype)
3. Manual fetch if you know the repository URL

---

## Version Deduplication

**GitHub API Limitation**: Returns only **current state** of repositories (default branch), not version-specific SBOMs.

**Example:**
- Your project uses `lodash@0.9.2` (2013) and `lodash@4.17.5` (2018)
- Both map to `lodash/lodash` repository
- GitHub API returns the **current state** (latest main/master branch)
- Not historical versions

**How We Handle It:**
1. Download each repository once
2. Name files by branch: `lodash_lodash_main.json`
3. Track version relationships in `version_mapping.json`

**Benefits:**
- ✅ 50% less storage (no duplicate content)
- ✅ Faster execution (fewer downloads)
- ✅ Accurate representation of API behavior
- ✅ Clear version-to-SBOM mapping

**For version-specific analysis:** Use package lockfiles (`package-lock.json`, `Pipfile.lock`) which contain exact dependency trees.

---

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest -q

# With coverage
pytest --cov=src/sbom_fetcher --cov-report=term-missing

# Specific test
pytest tests/test_sbom_service.py -v
```

Tests use mocked network calls - no real GitHub traffic.

---

## Documentation

### Additional Resources

See `docs/` folder for detailed documentation:

- **[LEGACY_README.md](docs/LEGACY_README.md)** - Original README with v1.0 HTML scraper details
- **[DEBUG_MAPPING_GUIDE.md](docs/DEBUG_MAPPING_GUIDE.md)** - Generic debugging guide for any repository
- **[DEBUG_RUN_ANALYSIS.md](docs/DEBUG_RUN_ANALYSIS.md)** - Complete analysis of beatBot test run
- **[FINAL_DIAGNOSTIC_SUMMARY.md](docs/FINAL_DIAGNOSTIC_SUMMARY.md)** - Comprehensive findings and solutions
- **[FIXES_SUMMARY.md](docs/FIXES_SUMMARY.md)** - All implemented fixes and their impact

### Legacy Information

- **[docs/LEGACY_README.md](docs/LEGACY_README.md)** - v1.0 HTML scraper documentation
- **[docs/BEATBOT_V1_V2_COMPARISON.md](docs/BEATBOT_V1_V2_COMPARISON.md)** - Performance comparison

---

## Use Cases

### Security Auditing
- Collect SBOMs for vulnerability scanning
- Track dependencies across versions
- Identify packages without GitHub repos

### Compliance & License Review
- SPDX 2.3 format for compliance tools
- Complete dependency trees for audits
- Track direct and transitive dependencies

### Dependency Analysis
- Understand dependency relationships
- Identify duplicate dependencies
- Map packages to source repositories

### Private Repository Management
- Works with private repos (API-based)
- Organization-wide SBOM collection
- Track internal and external dependencies

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure tests pass: `pytest -q`
5. Submit a pull request

---

## License

MIT License - see LICENSE file for details

---

## Support

- **Issues**: [GitHub Issues](https://github.com/tedg-dev/GitHub-SBOM-fetcher/issues)
- **Documentation**: This README and `docs/` folder
- **Debug Mode**: Use `--debug` flag for detailed diagnostics
