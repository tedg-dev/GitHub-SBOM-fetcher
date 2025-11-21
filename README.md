# GitHub SBOM Scraper & Fetcher

Tools for extracting and downloading Software Bill of Materials (SBOM) from GitHub repositories.

## Primary Tool: github_sbom_scraper.py

**Scrapes a repository's dependency graph and downloads SBOMs for all dependencies**

Perfect for security audits, vulnerability scanning, and dependency analysis. Matches the GitHub UI dependency graph with 97%+ accuracy.

### Key Features
- 🔍 **Comprehensive Scraping** - Extracts all dependencies from GitHub dependency graph pages
- 📦 **Complete SBOM Collection** - Downloads SBOM for root repo + all discovered dependencies
- 🔄 **Smart Version Handling** - Supports full semantic versioning (X.Y.Z-prerelease+build)
- 💾 **Resume Capability** - Progress tracking with ability to resume interrupted runs
- 📊 **Detailed Reporting** - Shows repositories with multiple versions and missing entries
- ⚡ **Rate Limit Handling** - Automatic retry logic with intelligent wait times
- 🎯 **97%+ Capture Rate** - Extracts nearly all dependencies shown in GitHub UI

### Quick Start
```bash
# Basic usage
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot

# With debug output
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --debug

# Resume interrupted run
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --resume sboms/sbom_export_2025-11-20_14.06.39
```

📖 **Full documentation:** [github_sbom_scraper_README.md](github_sbom_scraper_README.md)

---

## Secondary Tool: fetch_sbom.py

**Fetches SBOMs for all repositories accessible by your GitHub account(s)**

Useful for organization-wide SBOM collection across multiple repositories.

### Features
- Multi-account support via `keys.json`
- Lists all accessible repos using `/user/repos`
- Optional archived repos inclusion
- VS Code integration and pytest support

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

## Configure credentials (DO NOT COMMIT SECRETS)
Two supported formats for `keys.json`:

Single-account:
```json
{ "username": "your-user", "token": "ghp_..." }
```

Multi-account:
```json
{
  "accounts": [
    { "username": "acct1", "token": "ghp_..." },
    { "username": "acct2", "token": "ghp_..." }
  ]
}
```

Use `key.sample.json` in this repo as a template. Ensure `keys.json` is in `.gitignore`.

## Usage

### github_sbom_scraper.py (Recommended)

**Basic usage** - Scrape and download all dependency SBOMs:
```bash
python github_sbom_scraper.py --gh-user <owner> --gh-repo <repo>
```

**Example:**
```bash
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot
```

**Common options:**
```bash
# Debug mode - see detailed extraction logs
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --debug

# Resume interrupted run
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --resume sboms/sbom_export_2025-11-20_14.06.39

# Custom output directory
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --output-base-dir ./my_sboms
```

**Output structure:**
```
sboms/
  sbom_export_2025-11-20_14.06.39/
    tedg-dev_beatBot/
      tedg-dev_beatBot_root.json          # Root repository SBOM
      dependencies/                        # Dependency SBOMs (166+ files)
        babel_babel_7.0.0-beta.19.json
        lodash_lodash_4.17.5.json
        ...
      errors/                              # Error logs (if any)
        owner_repo_version_error.txt
      progress.json                        # Progress tracking
```

**What you get:**
- ✅ Root repository SBOM
- ✅ All dependency SBOMs (typically 150-200+ files)
- ✅ Version information for each dependency
- ✅ Progress tracking for resumable runs
- ✅ Error logs for dependencies with issues

📖 **See [github_sbom_scraper_README.md](github_sbom_scraper_README.md) for detailed documentation**

---

### fetch_sbom.py (For Multi-Repo Collection)

**Save SBOMs for all accessible repos:**
```bash
python fetch_sbom.py --key-file keys.json --output-dir sboms
```

**For specific account:**
```bash
python fetch_sbom.py --key-file keys.json --account acct2 --output-dir sboms
```

Output: `owner-repo-sbom.json` files in the output directory.

## VS Code
- Run/Debug: use the provided `.vscode/launch.json` ("Run fetch_sbom.py").
- Testing panel: pytest is enabled via `.vscode/settings.json` and `pytest.ini`.

## Testing
```bash
# optional dev deps
pip install -r requirements-dev.txt
# run tests
pytest -q
# with coverage
pytest --cov=fetch_sbom --cov-report=term-missing
```

The tests stub network calls; no real GitHub traffic is generated.

## npm Fallback Fix

The script now includes a fallback mechanism for npm packages where old versions point to non-existent GitHub repositories.

### Problem
Different npm versions can point to different repositories:
- `minimist@0.0.8` → `substack/minimist` (404 - doesn't exist)
- `minimist@1.2.8` → `minimistjs/minimist` (active with dependencies)

### Solution
The script automatically falls back to the latest version's repository when the specific version's repo doesn't exist.

### Verify the Fix
```bash
# Run the npm fallback test
PYTHONPATH=$PYTHONPATH:. pytest tests/test_fetch_sbom_hierarchy.py::TestGitHubSBOMFetcher::test_npm_fallback_mechanism -v

# Run all tests
PYTHONPATH=$PYTHONPATH:. pytest tests/ -v
```

## Troubleshooting

### github_sbom_scraper.py

**Missing dependencies** (GitHub UI shows more than scraper finds)
- Expected: ~97% capture rate due to JavaScript-loaded content
- Some npm packages don't have public GitHub repos
- Use `--debug` to see detailed extraction logs per page

**404 errors: "Dependency graph likely not enabled"**
- The repository has dependency graph disabled
- Check: https://github.com/owner/repo/network/dependencies

**Rate limits**
- Script automatically handles rate limiting with wait/retry
- If rate limited, it will pause and resume automatically

**Incomplete/interrupted runs**
- Use `--resume <dir>` to continue from where it stopped
- Example: `--resume sboms/sbom_export_2025-11-20_14.06.39`

**Low extraction count**
- Verify you're scraping the correct repository
- Check if dependency graph is enabled
- Use `--debug` to see what's being extracted vs skipped

---

### fetch_sbom.py

- **401/403**: Token scope or repo access missing
- **422 error**: Check input parameters  
- **Skipped repos**: SBOM not ready (202) or dependency graph disabled
- **Rate limits**: Script sleeps until reset automatically

## Security
- `keys.json` contains secrets. Do not commit it. Use `key.sample.json` as a template.
- Consider using a secrets manager for long-term storage and rotating tokens regularly.

## Repository setup (publishing under tedg-dev)
1) Initialize git and create first commit (do NOT add `keys.json`):
```bash
git init
python -m venv venv  # optional if not created yet
echo ""  # no-op placeholder
# Add everything, then unstage secrets just in case
git add .
# ensure keys.json and sboms are ignored; see .gitignore
git reset keys.json || true

git commit -m "Initial commit: GitHub SBOM fetcher"
```

2) Create public GitHub repo under the tedg-dev account (choose one):
- Using GitHub CLI (recommended):
```bash
# requires https://cli.github.com/ and gh auth login
# ensure you are authenticated as tedg-dev (gh auth status)
gh repo create tedg-dev/fetch-sbom \
  --public \
  --source=. \
  --remote=origin \
  --push
```
- Or create a public repo owned by tedg-dev at https://github.com/new named `fetch-sbom`, then:
```bash
git branch -M main
git remote add origin git@github.com:tedg-dev/fetch-sbom.git  # or https URL
git push -u origin main
```

## License
MIT
