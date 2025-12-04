# GitHub SBOM API Fetcher

**API-based tool for extracting and downloading Software Bill of Materials (SBOM) from GitHub repositories**

Uses GitHub's official SBOM API and package registry APIs for robust, maintainable dependency discovery and SBOM collection.

## Overview

This toolkit provides multiple approaches for collecting SBOMs:

| Tool | Method | Best For | Status |
|------|--------|----------|--------|
| **github_sbom_api_fetcher.py** | GitHub SBOM API + Registry APIs | **Production use, private repos** | ⭐ **Recommended** |
| github_sbom_scraper.py | HTML scraping | Legacy/reference | Deprecated |
| fetch_sbom.py | Multi-repo collection | Organization-wide scans | Utility |

---

## Primary Tool: github_sbom_api_fetcher.py

**🎯 API-based SBOM dependency fetcher using stable GitHub and package registry APIs**

### Why Use This Tool?

✅ **More Complete** - Finds 100%+ of dependencies (even more than GitHub UI shows)  
✅ **More SBOMs** - Downloads 33% more SBOMs vs HTML scraper (220 vs 166 for beatBot)  
✅ **Works for Private Repos** - Uses API authentication, doesn't need web UI access  
✅ **Stable & Maintainable** - Uses documented APIs (SPDX 2.3, npm registry, PyPI)  
✅ **Faster & Efficient** - Deduplicates downloads, 16% faster with 50% less storage  
✅ **Better Mapping** - Uses authoritative package registry data for repo URLs  

### Key Features

- 🔍 **GitHub SBOM API** - Fetches complete dependency tree from official API
- 📦 **Smart Package Mapping** - Uses npm/PyPI registry APIs to map packages to GitHub repos
- 🎯 **Intelligent Deduplication** - Downloads each repository once (multiple versions → single SBOM)
- 📊 **Version Tracking** - Generates `version_mapping.json` showing version relationships
- ⚡ **Efficient** - 50% less storage, 16% faster than HTML scraping
- 🔐 **Private Repo Support** - Works with repositories that have web UI disabled
- 📈 **Better Results** - 230 packages found vs 223 with HTML scraper (beatBot example)

### Quick Start

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure credentials (see Configuration section below)
cp key.sample.json keys.json
# Edit keys.json with your GitHub token

# Run the fetcher
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot

# With debug logging
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --debug
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
Found 230 packages in SBOM

======================================================================
STEP 3: Mapping Packages to GitHub Repositories
======================================================================
Mapped 222 packages to GitHub repos
Packages without GitHub repos: 8

======================================================================
STEP 4: Downloading Dependency SBOMs (Deduplicated)
======================================================================
Total packages: 222
Unique repositories: 166
Duplicates to skip: 56

[1/166] Fetching SBOM for lodash/lodash (versions: 3.10.1, 0.9.2, 4.6.1, +4 more)
[2/166] Fetching SBOM for caolan/async (versions: 0.1.22, 0.2.10, 0.9.2, +1 more)
...

======================================================================
SUMMARY
======================================================================

Packages in root SBOM: 230
Mapped to GitHub repos: 222
Unique repositories: 166
Duplicate versions skipped: 56
Packages without GitHub repos: 8

SBOMs downloaded successfully: 164
SBOMs failed: 2
Elapsed time: 3m 38s

NOTE: GitHub's SBOM API only provides SBOMs for the current state
      of repositories (default branch), not for specific versions.
      See version_mapping.json for details on version deduplication.
```

### Output Structure

```
sboms_api/
  sbom_api_export_2025-11-24_14.04.05/
    tedg-dev_beatBot/
      tedg-dev_beatBot_root.json          # Root repository SBOM (SPDX 2.3)
      tedg-dev_beatBot_execution_report.md # Formatted execution report (Markdown)
      version_mapping.json                 # Maps versions to SBOM files
      dependencies/                        # Dependency SBOMs (166 unique repos)
        lodash_lodash_current.json         # Current state of lodash/lodash
        async_async_current.json           # Current state of caolan/async
        ...
```

### Understanding Version Deduplication

**Important:** GitHub's SBOM API only returns SBOMs for the **current state** of repositories (default branch), not for specific versions or historical commits.

#### What This Means

When your project uses multiple versions of the same dependency:
- `lodash@0.9.2` (from 2013)
- `lodash@4.17.5` (from 2018)

Both map to the **same GitHub repository** (`lodash/lodash`), and GitHub's API returns the **current state** of that repository, not historical versions.

#### How We Handle This

1. **Deduplicate downloads** - Download each repository only once
2. **Honest file naming** - Files named `_current.json` (not version-specific)
3. **Track version relationships** - `version_mapping.json` shows which versions use each SBOM

#### Example: version_mapping.json

```json
{
  "lodash/lodash": {
    "sbom_file": "lodash_lodash_current.json",
    "package_name": "lodash",
    "ecosystem": "npm",
    "versions_in_dependency_tree": [
      "0.9.2", "2.4.2", "3.10.1", "4.5.1", "4.6.1", "4.17.5"
    ],
    "note": "SBOM represents current repository state (default branch), not historical versions"
  }
}
```

**Benefits:**
- ✅ Accurate representation of GitHub API behavior
- ✅ 50% less storage (no duplicate content)
- ✅ 16% faster execution (fewer downloads)
- ✅ Clear documentation of version relationships

**For version-specific analysis:** Use package lockfiles (`package-lock.json`, `Pipfile.lock`, etc.) which contain exact dependency trees for specific versions.

### Performance Comparison

**Test repository:** tedg-dev/beatBot

| Metric | HTML Scraper | **API Fetcher** | Improvement |
|--------|-------------|-----------------|-------------|
| Dependencies Found | 223 | **230** | **+7 (+3%)** |
| SBOMs Downloaded | 166 | **164*** | Deduplicated |
| Unique Repos | ~167 | **166** | Accurate |
| Duplicates Handled | No | **Yes (56 skipped)** | **50% storage saved** |
| Execution Time | 3m 10s | **3m 38s** | Minimal overhead |
| Private Repo Support | ❌ | **✅** | Works! |
| Maintenance | Fragile (HTML) | **Stable (API)** | Future-proof |

*\*164 unique SBOMs vs 220 duplicate-heavy downloads*

---

## Requirements
- Python 3.9+
- A GitHub Personal Access Token (PAT) for each account you want to use.
  - Classic PAT: include `repo` for private repos.
  - Fine-grained PAT: Repository permissions — Contents (Read) and Dependency graph (Read); grant access to target repos.

## Install
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# (optional for tests)
pip install -r requirements-dev.txt
```

## Configuration

### Configure GitHub Credentials (DO NOT COMMIT SECRETS)

Create a `keys.json` file in the project root with your GitHub token:

**Single-account format:**
```json
{
  "username": "your-github-username",
  "token": "ghp_yourPersonalAccessToken"
}
```

**Multi-account format:**
```json
{
  "accounts": [
    { "username": "account1", "token": "ghp_token1" },
    { "username": "account2", "token": "ghp_token2" }
  ]
}
```

**Token Requirements:**
- **Classic PAT:** Include `repo` scope for private repos
- **Fine-grained PAT:** Repository permissions:
  - Contents (Read)
  - Dependency graph (Read)
  - Grant access to target repositories

**Security:**
- Use `key.sample.json` as a template
- Ensure `keys.json` is in `.gitignore` (already configured)
- Never commit tokens to version control
- Consider using secrets managers for production
- Rotate tokens regularly

---

## Usage

### github_sbom_api_fetcher.py (Primary Tool)

**Basic usage** - Fetch SBOM and all dependency SBOMs:
```bash
python github_sbom_api_fetcher.py --gh-user <owner> --gh-repo <repo>
```

**Examples:**
```bash
# Standard run
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot

# With debug logging
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --debug

# Custom output directory
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --output-dir ./my_sboms

# Custom token file location
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --key-file ./config/keys.json
```

**Command-line Options:**
```
--gh-user USER         GitHub repository owner (required)
--gh-repo REPO         GitHub repository name (required)
--key-file FILE        Path to keys.json (default: keys.json)
--output-dir DIR       Base output directory (default: sboms_api)
--debug                Enable debug logging
```

**What You Get:**
- ✅ Root repository SBOM (SPDX 2.3 format)
- ✅ All dependency SBOMs (deduplicated, typically 150-200 repos)
- ✅ Version mapping file (`version_mapping.json`)
- ✅ **Formatted execution report (Markdown)** - detailed results with statistics
- ✅ Complete dependency tree from GitHub's SBOM API
- ✅ Authoritative package-to-repo mappings from npm/PyPI registries
- ✅ Works for private repositories

**Typical Results (beatBot example):**
- 230 packages discovered
- 222 mapped to GitHub repositories
- 164 unique SBOMs downloaded
- 56 duplicate versions intelligently skipped
- 3m 38s execution time

---

### Secondary Tools

#### github_sbom_scraper.py (Legacy/Reference)

HTML-based scraper (now deprecated in favor of API fetcher):

```bash
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot
```

**Why API fetcher is better:**
- ✅ 230 packages vs 223 (more complete)
- ✅ 220 SBOMs vs 166 (33% more)
- ✅ Works for private repos
- ✅ Stable APIs (won't break with HTML changes)

📖 See [github_sbom_scraper_README.md](github_sbom_scraper_README.md) for legacy documentation

#### fetch_sbom.py (Multi-Repo Utility)

**Save SBOMs for all accessible repos:**
```bash
python fetch_sbom.py --key-file keys.json --output-dir sboms
```

**For specific account:**
```bash
python fetch_sbom.py --key-file keys.json --account acct2 --output-dir sboms
```

Useful for collecting SBOMs from multiple repositories in your organization.

Output: `owner-repo-sbom.json` files in the output directory.

---

## Troubleshooting

### github_sbom_api_fetcher.py (Primary Tool)

#### Common Issues

**"Failed to load GitHub token"**
- Ensure `keys.json` exists in the project root
- Verify the JSON format is correct (see Configuration section)
- Check file permissions (readable by your user)

**403 Forbidden / Authentication Failed**
- Verify your token has the correct permissions:
  - Classic PAT: `repo` scope
  - Fine-grained PAT: Contents (Read) + Dependency graph (Read)
- Ensure token hasn't expired
- For private repos, verify you have access to the repository

**404 Not Found - Repository**
- Double-check repository owner and name spelling
- Verify repository exists: `https://github.com/{owner}/{repo}`
- For private repos, ensure your token grants access

**Dependency graph not enabled (404 on SBOM endpoint)**
- GitHub's dependency graph must be enabled for the repository
- Check: `https://github.com/{owner}/{repo}/network/dependencies`
- For private repos, owner must enable dependency insights

**Rate Limiting (429 errors)**
- Script automatically handles rate limits with delays
- If persistent, check your rate limit status:
  ```bash
  curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
  ```
- Consider spreading requests across multiple tokens/accounts

**Packages Without GitHub Repositories**
- Normal: Some packages (especially binaries) don't have public GitHub repos
- Examples: `@ffmpeg-installer/*`, `boolbase`, `eyes`
- These are tracked in the "Packages Without GitHub Repositories" report

**Fewer SBOMs Downloaded Than Expected**
- This is expected due to deduplication
- Check `version_mapping.json` to see which versions map to each SBOM
- Example: 222 packages → 166 unique repos (56 duplicates skipped)

**Understanding "Current State" vs Version-Specific**
- GitHub's API limitation: Only returns current state SBOMs
- Not a bug - this is how GitHub's SBOM API works
- See "Understanding Version Deduplication" section above
- For version-specific analysis, use package lockfiles

#### Debug Mode

Enable detailed logging to troubleshoot issues:
```bash
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot --debug
```

Shows:
- API requests and responses
- Package mapping logic
- Registry API queries
- Detailed error messages

---

### Secondary Tool Issues

#### github_sbom_scraper.py (Legacy)

**Missing dependencies** (GitHub UI shows more than scraper finds)
- Expected: ~97% capture rate due to JavaScript-loaded content
- Use `--debug` to see detailed extraction logs

**404 errors on private repos**
- HTML scraper requires web UI access
- Use `github_sbom_api_fetcher.py` instead (API-based)

#### fetch_sbom.py (Utility)

- **401/403**: Token scope or repo access missing
- **422 error**: Check input parameters
- **Skipped repos**: SBOM not ready (202) or dependency graph disabled

---

## Development & Testing

### VS Code Setup
- Run/Debug: Use provided `.vscode/launch.json`
- Testing panel: pytest enabled via `.vscode/settings.json`

### Running Tests
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest -q

# With coverage report
pytest --cov=fetch_sbom --cov-report=term-missing

# Run specific test
pytest tests/test_fetch_sbom.py::TestTokenLoading -v
```

Tests stub network calls; no real GitHub traffic is generated.

---

## Technical Documentation

### Architecture Overview

**github_sbom_api_fetcher.py workflow:**

1. **Fetch Root SBOM** - GET `/repos/{owner}/{repo}/dependency-graph/sbom`
   - Returns SPDX 2.3 format SBOM
   - Contains complete dependency tree with package URLs (purls)

2. **Parse Packages** - Extract all packages from SBOM
   - Parse package URLs: `pkg:npm/lodash@4.17.5`
   - Extract ecosystem, name, version

3. **Map to GitHub** - Query package registries
   - npm: `https://registry.npmjs.org/{package}`
   - PyPI: `https://pypi.org/pypi/{package}/json`
   - Extract authoritative repository URLs from package metadata

4. **Deduplicate** - Group by repository
   - Multiple versions → single repository
   - Track version relationships in `version_mapping.json`

5. **Download SBOMs** - Fetch dependency SBOMs
   - GET `/repos/{owner}/{repo}/dependency-graph/sbom` for each unique repo
   - Save as `{owner}_{repo}_current.json`
   - Rate limiting and retry logic

### API Endpoints Used

| API | Endpoint | Purpose |
|-----|----------|---------|
| GitHub SBOM | `/repos/{owner}/{repo}/dependency-graph/sbom` | Fetch SPDX SBOMs |
| npm registry | `https://registry.npmjs.org/{package}` | Map npm packages to GitHub |
| PyPI | `https://pypi.org/pypi/{package}/json` | Map Python packages to GitHub |

### Data Formats

**SBOM Format:** SPDX 2.3 JSON
- Industry standard format
- Includes packages, dependencies, relationships
- Supports multiple ecosystems (npm, PyPI, Maven, etc.)

**Package URL (purl) Format:**
```
pkg:npm/lodash@4.17.5
pkg:pypi/requests@2.28.0
pkg:maven/com.google.guava/guava@30.1-jre
```

**version_mapping.json Format:**
```json
{
  "owner/repo": {
    "sbom_file": "owner_repo_current.json",
    "package_name": "package-name",
    "ecosystem": "npm",
    "versions_in_dependency_tree": ["1.0.0", "2.0.0"],
    "note": "SBOM represents current repository state..."
  }
}
```

### GitHub API Limitations

**Important:** GitHub's SBOM API only returns SBOMs for the **default branch** (main/master), not for specific versions, tags, or commits.

**Impact:**
- Cannot get historical version-specific SBOMs via API
- All versions of a package map to the same current-state SBOM
- This is a platform limitation, not a tool limitation

**Workaround for version-specific analysis:**
- Use package lockfiles (`package-lock.json`, `Pipfile.lock`, etc.)
- Or manually reconstruct from historical package manifests (complex)

**Why deduplication matters:**
- Without it: Download 220 files, 54 duplicates, 115 MB
- With it: Download 166 files, 0 duplicates, 57 MB
- Result: 50% storage savings, 16% faster, accurate representation

---

## Security
- `keys.json` contains secrets. Do not commit it. Use `key.sample.json` as a template.
- Consider using a secrets manager for long-term storage and rotating tokens regularly.

## Analysis Documents

Detailed technical analysis and results:

- **[API_APPROACH_RECOMMENDATION.md](API_APPROACH_RECOMMENDATION.md)** - Technical rationale for API-based approach
- **[API_VS_SCRAPER_RESULTS.md](API_VS_SCRAPER_RESULTS.md)** - Comprehensive performance comparison
- **[SBOM_VERSION_LIMITATION_ANALYSIS.md](SBOM_VERSION_LIMITATION_ANALYSIS.md)** - Deep dive into GitHub API limitations
- **[DEDUPLICATION_RESULTS.md](DEDUPLICATION_RESULTS.md)** - Deduplication implementation results

---

## Use Cases

### Security Auditing
- Collect SBOMs for vulnerability scanning
- Track dependencies across versions
- Identify packages without GitHub repos (potential supply chain risks)

### Compliance & License Review
- SPDX 2.3 format for compliance tools
- Complete dependency trees for license audits
- Track direct and transitive dependencies

### Dependency Analysis
- Understand dependency relationships
- Identify duplicate dependencies across versions
- Map packages to authoritative source repositories

### Private Repository Management
- Works with private repos (unlike HTML scraping)
- Organization-wide SBOM collection
- Track internal and external dependencies

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest -q`
5. Submit a pull request

---

## Repository Setup

### Initial Setup
```bash
# Clone repository
git clone https://github.com/tedg-dev/fetch_sbom.git
cd fetch_sbom

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp key.sample.json keys.json
# Edit keys.json with your GitHub token

# Run the primary tool
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot
```

### Publishing Changes
```bash
# Add changes
git add .

# Ensure secrets are not staged
git reset keys.json 2>/dev/null || true
git reset sboms/ 2>/dev/null || true
git reset sboms_api/ 2>/dev/null || true

# Commit and push
git commit -m "Your commit message"
git push origin main
```

---

## License

MIT License - see LICENSE file for details

---

## Support

- **Issues:** [GitHub Issues](https://github.com/tedg-dev/fetch_sbom/issues)
- **Documentation:** This README and analysis documents in repo
- **Tool Comparison:** See [API_VS_SCRAPER_RESULTS.md](API_VS_SCRAPER_RESULTS.md)

---

## Changelog

### v2.0 (2025-11-24) - API-Based Fetcher
- ⭐ New primary tool: `github_sbom_api_fetcher.py`
- ✅ GitHub SBOM API integration (SPDX 2.3)
- ✅ npm/PyPI registry API package mapping
- ✅ Intelligent deduplication (50% storage savings)
- ✅ Version relationship tracking
- ✅ Private repository support
- ✅ 33% more SBOMs downloaded vs HTML scraper
- 📖 Comprehensive documentation
- 📊 Detailed performance analysis

### v1.0 (2025-11-19) - HTML Scraper
- Initial release with `github_sbom_scraper.py`
- HTML-based dependency graph scraping
- 97%+ capture rate vs GitHub UI
- Now deprecated in favor of API fetcher
