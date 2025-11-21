# GitHub SBOM Fetcher

Fetches Dependency Graph SBOMs for repositories from GitHub. Includes two tools:

1. **`fetch_sbom.py`** - Fetches SBOMs for all repos accessible by your GitHub account(s)
2. **`github_sbom_scraper.py`** - Scrapes a specific repo's dependency graph and downloads all dependency SBOMs

## Features

### fetch_sbom.py
- Multi-account support via a single `keys.json` (or single-account format).
- Lists all accessible repos using `/user/repos` with affiliation.
- Saves SBOM JSON as `owner-repo-sbom.json`.
- Handles rate limits and common SBOM response cases (200 saved, 202/403/404 skipped).
- Optional archived repos inclusion.
- VS Code run/debug and testing integration (pytest).

### github_sbom_scraper.py
- Scrapes GitHub dependency graph pages to extract all dependencies
- Downloads SBOM for each discovered dependency
- Supports full semantic versioning (X.Y.Z-prerelease+build)
- Progress tracking with resume capability for interrupted runs
- Automatic pagination across all dependency graph pages
- Detailed reporting of repositories with multiple versions
- 97%+ capture rate of dependencies shown in GitHub UI

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

### fetch_sbom.py
Save SBOMs for all accounts in `keys.json`:
```bash
python fetch_sbom.py --key-file keys.json --output-dir sboms
```

Only for a specific account (by username/login):
```bash
python fetch_sbom.py --key-file keys.json --account acct2 --output-dir sboms
```

Include archived repos:
```bash
python fetch_sbom.py --key-file keys.json --include-archived --output-dir sboms
```

Output files: `owner-repo-sbom.json` inside the chosen output dir.

### github_sbom_scraper.py
Scrape dependencies and download SBOMs for a specific repository:
```bash
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot
```

With debug output for troubleshooting:
```bash
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --debug
```

Resume a previous interrupted run:
```bash
python github_sbom_scraper.py --gh-user tedg-dev --gh-repo beatBot --resume <export_dir>
```

Output structure:
```
sboms/
  sbom_export_2025-11-20_14.06.39/
    tedg-dev_beatBot/
      tedg-dev_beatBot_root.json          # Root repository SBOM
      dependencies/                        # Dependency SBOMs
        owner_repo_version.json
        ...
      errors/                              # Error logs
      progress.json                        # Progress tracking file
```

See [github_sbom_scraper_README.md](github_sbom_scraper_README.md) for detailed documentation.

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

### fetch_sbom.py
- 401/403 on token validation: token scope or repo access missing.
- 422 listing error: we avoid incompatible `type` with `affiliation` (fixed). If you still see 422, check inputs.
- Skipped repos: SBOM 202 (not ready) or Dependency Graph disabled.
- Rate limits: script sleeps until reset when needed.
- "Not found" errors for npm dependencies: The fallback mechanism should handle these automatically.

### github_sbom_scraper.py
- **Missing dependencies**: GitHub UI shows 229 but scraper finds 223 (~97%)
  - Expected due to JavaScript-loaded content not in static HTML
  - Some npm packages may not have public GitHub repos
- **404 errors**: "Dependency graph likely not enabled" - repository has dependency graph disabled
- **Rate limits**: Script automatically handles rate limiting with wait/retry
- **Incomplete runs**: Use `--resume <dir>` to continue from last progress
- **Low capture rate**: Use `--debug` to see detailed extraction logs per page

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
