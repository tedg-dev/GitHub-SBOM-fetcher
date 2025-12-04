# `github_sbom_scraper.py`

Scrape the GitHub **Dependency graph → Dependencies** UI for a repository, derive the set of dependent GitHub repositories (including multiple versions of the same repo), and export SBOMs for the root repo and all dependencies via the GitHub Dependency Graph SBOM REST API.

This tool is intended to give you a faithful, debuggable export that matches what you see in the GitHub **Insights → Dependency graph → Dependencies** page, rather than relying on heuristic npm/registry mapping.

---

## 🆕 Recent Improvements (November 2025)

The script now includes production-ready resilience features:

- **✅ Rate limit handling**: Automatically detects HTTP 429 responses, monitors rate limit headers, and waits appropriately before retrying.
- **✅ Retry logic with exponential backoff**: Automatically retries transient failures (429, 500+, network errors) up to 3 times (configurable) with smart backoff delays.
- **✅ Progress persistence**: Saves progress after each download and supports `--resume` to continue interrupted runs without re-downloading completed SBOMs.

These improvements make the script robust for large repositories and unreliable networks, significantly reducing failures from rate limits and transient errors.

---

## Features

- Scrapes the GitHub **network/dependencies** page for a given repo.
- Follows pagination to cover all dependency pages.
- Extracts a GitHub `owner/repo` and a version string for **each** dependency row.
- Calls the GitHub **SBOM REST API** for:
  - The root repository.
  - Every dependency `owner/repo` pair discovered from the UI.
- **Rate limit handling:**
  - Automatically detects and handles HTTP 429 (rate limit) responses.
  - Monitors `X-RateLimit-Remaining` header and proactively waits when approaching limits.
  - Respects `Retry-After` and `X-RateLimit-Reset` headers from GitHub.
- **Automatic retry logic:**
  - Retries failed requests with exponential backoff (2s → 4s → 8s).
  - Handles transient errors (500+) and network failures.
  - Configurable retry attempts and delays.
- **Progress persistence:**
  - Saves progress after each successful SBOM download.
  - Resume interrupted runs without re-downloading completed SBOMs.
  - Tracks both successful and failed repositories.
- Saves SBOMs and per-dependency error logs in a structured directory tree.
- Provides rich debug logging suitable for troubleshooting and for driving the tool via VS Code.

---

## Requirements

- Python 3.8+ (same as the rest of the project).
- Dependencies (see `requirements.txt`):
  - `requests`
  - `beautifulsoup4`
  - `python-dateutil` (used elsewhere in the project but harmless here)

Install with:

```bash
pip install -r requirements.txt
```

---

## Credentials: `keys.json`

`github_sbom_scraper.py` expects a JSON credentials file named `keys.json` in the current directory that contains a GitHub Personal Access Token (PAT).

**Supported JSON formats:**

1. **Single token:**

   ```json
   {
     "github_token": "ghp_..."
   }
   ```

2. **Multiple accounts:**

   ```json
   {
     "accounts": [
       { "username": "user1", "token": "ghp_..." },
       { "username": "user2", "token": "ghp_..." }
     ]
   }
   ```

   - The script uses the **first account with a non-empty token** that is not `"<PASTE_TOKEN_HERE>"`.

3. **Generic token fields (backwards compatibility):**

   ```json
   { "username": "user", "token": "ghp_..." }
   ```

   or

   ```json
   { "token": "ghp_..." }
   ```

If no usable token is found, the script logs an error and exits with code `1`.

---

## Command-line interface

Run the script with:

```bash
python github_sbom_scraper.py \
  --gh-user <owner> \
  --gh-repo <repo> \
  [--output-dir sboms] \
  [--debug] \
  [--max-retries N] \
  [--retry-delay SECONDS] \
  [--request-delay SECONDS] \
  [--resume]
```

### Arguments

#### Required Arguments

- `--gh-user` (required)
  - GitHub owner/user name of the repository, e.g. `tedg-dev`.

- `--gh-repo` (required)
  - Repository name, e.g. `beatBot`.

#### Optional Arguments

- `--output-dir` (optional, default `sboms`)
  - Base directory under which all SBOM exports and error files are written.

- `--debug` (optional flag)
  - Enables verbose debug logging.
  - Useful when comparing counts with the GitHub UI or debugging network/HTML parsing issues.

#### Retry and Rate Limiting Arguments

- `--max-retries` (optional, default `3`)
  - Maximum number of retry attempts for failed API requests.
  - Applies to HTTP 429 (rate limit), 500+ (server errors), and network failures.
  - Set to `1` to disable retries.

- `--retry-delay` (optional, default `2.0`)
  - Base delay in seconds for exponential backoff.
  - Actual delays: `retry-delay × 2^attempt` (e.g., 2s, 4s, 8s).
  - Rate limit responses use GitHub's suggested wait time when available.

- `--request-delay` (optional, default `0.5`)
  - Delay in seconds between consecutive API requests.
  - Helps avoid hitting rate limits on large repositories.
  - Set to `0` for no delay (not recommended for large batches).

#### Progress Resumption Arguments

- `--resume` (optional flag)
  - Resume from the most recent progress file.
  - Automatically finds and loads the latest `progress.json` in the output directory.
  - Skips already-downloaded SBOMs and continues from where the script left off.
  - Useful for recovering from interruptions or rate limit exhaustion.

Return code is `0` on normal completion (even if some individual dependencies fail), and non-zero (typically `1`) when a fatal setup/scraping error occurs.

---

## How it works

### 1. Scraping the GitHub dependency graph UI

For a given `--gh-user owner` and `--gh-repo repo`, the script targets:

```text
https://github.com/<owner>/<repo>/network/dependencies
```

The flow:

1. Build a `requests.Session` with the GitHub token and a user agent.
2. GET the `network/dependencies` page.
3. Parse the HTML with `BeautifulSoup` using the built-in `html.parser`.
4. Extract a list of **dependency entries** from each page.
5. Follow pagination using a `rel="next"` link or a "Next"/"Next ›" anchor, until there are no more pages.

Each dependency entry is represented as:

```python
@dataclass
class Dependency:
    owner: str
    repo: str
    version: str  # may be empty if version cannot be inferred
```

**Owner/repo extraction:**

- For each `<a>` element in the page, the script checks its `href`:
  - If it looks like `/OWNER/REPO` or `https://github.com/OWNER/REPO`:
    - It strips query/hash parts.
    - It splits the path and validates that it’s exactly `owner/repo`.

**Version extraction:**

- The script searches starting from the anchor's **parent container** (since "Direct"/"Transitive" labels are siblings, not parents of the link).
- It walks up to **6 parent levels** looking for text that:
  - Contains `"Transitive"` or `"Direct"` (marking it as a dependency).
  - Contains a version-like substring matching `\d+\.\d+(\.\d+)*`.
- The version string is stored as-is; if none is found, `version` will be `""` and later mapped to `"unknown"` for filenames.

**Deduplication:**

- **Per-page deduplication**: Each `owner/repo@version` combination is counted once per page.
  - For entries without versions, a counter ensures each occurrence is unique (matching GitHub's count).
- **Cross-page**: Same `owner/repo@version` can appear on multiple pages and will be counted each time (matching GitHub's UI behavior).
- **Result**: Total dependency count matches what GitHub displays (e.g., 223 entries for beatBot, where some repos appear with multiple versions).

### 2. Downloading SBOMs via GitHub REST API

SBOMs are fetched using the GitHub Dependency Graph SBOM endpoint:

```text
GET https://api.github.com/repos/{owner}/{repo}/dependency-graph/sbom
```

The script calls this endpoint for:

1. **The root repository** (`--gh-user` / `--gh-repo`).
2. **Each dependency** (`Dependency.owner` / `Dependency.repo`).

#### Request behavior with retry logic

For each SBOM request, the script implements a robust retry mechanism:

**Rate limit handling:**

- **Before each request**: Checks `X-RateLimit-Remaining` header from previous response.
  - If < 5 requests remaining, warns and calculates wait time from `X-RateLimit-Reset`.
- **On HTTP 429 (Rate Limit Exceeded)**:
  - Checks `Retry-After` header or uses `X-RateLimit-Reset` to determine wait time.
  - Defaults to 60 seconds if no header information is available.
  - Waits the specified duration and retries (up to `--max-retries` attempts).

**Response handling:**

- On **200 OK**:
  - Attempts to parse the body as JSON.
  - If JSON parsing fails, logs an error and treats the SBOM as unavailable.

- On **403, 404, or 202** (permanent failures):
  - Treated as "SBOM not available".
  - A warning is logged; no retry is attempted.

- On **429 (Rate Limit)** or **500+ (Server Errors)**:
  - Retries up to `--max-retries` times with exponential backoff.
  - For 429: Uses rate limit headers to determine optimal wait time.
  - For 500+: Uses exponential backoff (2s, 4s, 8s by default).
  - Logs warning on each retry attempt with retry count and delay.

- On **network/requests exceptions** (timeouts, DNS failures, etc.):
  - Retries up to `--max-retries` times with exponential backoff.
  - Logs the exception and retry attempt details.

**Request pacing:**

- After each request (success or final failure), waits `--request-delay` seconds.
- This helps maintain compliance with rate limits across many requests.

**Progress tracking:**

- After each successful SBOM download, updates `progress.json`.
- Tracks completed and failed repositories for resumption capability.

---

## Output directory structure

The script writes all outputs under the path specified by `--output-dir` (default `sboms`).

For a run at a given moment, it creates:

```text
<output-dir>/
  sbom_export_YYYY-MM-DD_HH.MM.SS/
    <owner>_<repo>/
      <owner>_<repo>-sbom.json
      <owner>_<repo>-sbom.error.txt   # only if root SBOM cannot be fetched/saved
      progress.json                    # tracks download progress for resumption
      dependencies/
        <dep_owner>_<dep_repo>_<version>.json
        <dep_owner>_<dep_repo>_<version>.error.txt
```

### Progress file

- File: `progress.json`
- Contains:
  - `timestamp`: When the export started.
  - `base_dir`: Full path to the export directory.
  - `root_downloaded`: Whether the root SBOM was successfully downloaded.
  - `completed_repos`: List of completed dependency identifiers (format: `owner/repo@version`).
  - `failed_repos`: List of failed dependency identifiers.
- Updated after each successful or failed SBOM download.
- Used by `--resume` to skip already-processed repositories.

### Root repository SBOM

- File: `<owner>_<repo>-sbom.json` (e.g., `tedg-dev_beatBot-sbom.json`).
- If fetching or saving the root SBOM fails:
  - An error file `<owner>_<repo>-sbom.error.txt` is created containing a human-readable reason (e.g., HTTP status or exception).

### Dependency SBOMs

For each scraped dependency `owner/repo` with version `v`:

- The version used in the filename is:
  - `v` if non-empty, with `/` and `\` replaced by `_`.
  - `"unknown"` if no version could be inferred.

- SBOM success case:

  ```text
  dependencies/<dep_owner>_<dep_repo>_<v>.json
  ```

- Error/unavailable case:

  ```text
  dependencies/<dep_owner>_<dep_repo>_<v>.error.txt
  ```

  The `.error.txt` file contains a short, plain-text explanation:
  - `"Dependency graph is disabled for this repository"` - Feature disabled by owner.
  - `"SBOM not available or request failed"` - Generic failure.
  - Exception messages for other errors.

---

## Logging and debug mode

### Log configuration

Logging is configured in `main()` as:

- `INFO` level by default.
- `DEBUG` level when `--debug` is passed.

Format:

```text
YYYY-MM-DD HH:MM:SS,mmm - LEVEL - message
```

Logs are written to stdout via a `StreamHandler`, which integrates cleanly with VS Code’s debug console and integrated terminal.

### What you see in logs

At `INFO` level:

- Which dependency pages are being fetched.
- Total number of dependency entries scraped.
- Progress through dependencies:
  - `[%d/%d] Fetching SBOM for owner/repo@version`
- Success/failure messages for each dependency SBOM.
- Final summary with counts and output directory.

At `DEBUG` level (recommended for troubleshooting):

- More details about HTML parsing and version detection.
- URLs used for SBOM requests.
- Error messages from JSON decoding issues.
- Any other low-level diagnostics that can help understand mismatches with the GitHub UI.

---

## Error handling behavior

### Fatal errors (script exits early)

Examples:

- Credentials file missing or unreadable.
- No usable token found in the JSON.
- Failure to fetch the GitHub dependencies page (e.g., non-200 response, network error).

These result in:

- A logged error describing the failure.
- Exit code `1`.
- No SBOM files written for that run.

### Non-fatal per-repo errors with automatic retry

Once scraping succeeds and dependencies are known, **SBOM fetch failures for individual repos are treated as non-fatal**:

**Transient errors (automatically retried):**

- **HTTP 429 (Rate Limit)**: Retries after waiting per GitHub's rate limit headers.
- **HTTP 500+** (Server Errors): Retries with exponential backoff (2s, 4s, 8s).
- **Network failures** (timeouts, DNS issues): Retries with exponential backoff.

If all retry attempts fail:

- The script logs a final error with details of all attempts.
- Continues processing other dependencies.
- Creates an `.error.txt` file for the failed dependency.
- Marks the repository as "failed" in `progress.json`.

**Permanent errors (not retried):**

- **HTTP 403** (Forbidden): SBOM access denied or private repo.
- **HTTP 404** (Not Found): SBOM not available for this repository.
- **HTTP 202** (Accepted): SBOM generation in progress (GitHub side).
- **JSON parsing errors**: Invalid response body.
- **Dependency graph disabled**: Repository owner has disabled the dependency graph feature.

These are logged as warnings and the script immediately moves to the next dependency.

**Disabled dependency graph detection:**

When an SBOM fetch fails with 404, the script automatically checks the repository's dependency graph page to determine if the feature is disabled. If detected:

- Logs: `WARNING - Dependency graph is disabled for owner/repo`
- Error file contains: `"Dependency graph is disabled for this repository"`

This helps distinguish between "SBOM not available" and "feature disabled by owner".

**Summary and resumption:**

- Summary counts at the end include:
  - Total dependencies scraped.
  - Successfully downloaded.
  - Failed or unavailable (after all retries).
- Failed repositories are tracked in `progress.json`.
- Using `--resume` allows you to retry failed repositories in a subsequent run (e.g., after rate limits reset).

This design lets you:

- **Automatically recover** from transient network and rate limit issues.
- **Resume interrupted runs** without re-downloading successful SBOMs.
- **Identify permanent gaps** in coverage via `.error.txt` files.
- **Inspect the exact error message** for each failure.
- **Re-run later** with `--resume` if issues are resolved.

---

## Examples

### Basic run for `tedg-dev/beatBot`

```bash
python github_sbom_scraper.py \
  --gh-user tedg-dev \
  --gh-repo beatBot \
  --output-dir sboms
```

### With debug logging enabled

```bash
python github_sbom_scraper.py \
  --gh-user tedg-dev \
  --gh-repo beatBot \
  --output-dir sboms \
  --debug
```

### Resume an interrupted run

If the script was interrupted (Ctrl+C, network failure, or rate limit exhaustion):

```bash
python github_sbom_scraper.py \
  --gh-user tedg-dev \
  --gh-repo beatBot \
  --output-dir sboms \
  --resume
```

This automatically:
- Finds the most recent `progress.json` file.
- Skips already-downloaded SBOMs.
- Continues downloading from where it left off.

### Custom retry configuration for large repositories

For repositories with many dependencies or unreliable networks:

```bash
python github_sbom_scraper.py \
  --gh-user tedg-dev \
  --gh-repo beatBot \
  --output-dir sboms \
  --max-retries 5 \
  --retry-delay 3.0 \
  --request-delay 1.0
```

This uses:
- 5 retry attempts (instead of 3).
- Longer backoff delays: 3s, 6s, 12s, 24s, 48s.
- 1 second delay between requests (more conservative rate limiting).

### Aggressive mode (not recommended)

Disable retries and delays for testing or small repositories:

```bash
python github_sbom_scraper.py \
  --gh-user tedg-dev \
  --gh-repo small-repo \
  --output-dir sboms \
  --max-retries 1 \
  --request-delay 0
```

⚠️ **Warning**: This may hit rate limits quickly on large repositories.

### Checking results

After running, check:

- The timestamped export directory under `sboms/`.
- The `tedg-dev_beatBot` folder for the root SBOM.
- The `dependencies/` folder for per-repository SBOM JSON files and any `.error.txt` files.
- The `progress.json` file to see completed and failed repositories.

You can compare:

- The count of dependency entries scraped (printed in the summary and logs), with
- The count displayed in GitHub's Dependency graph UI, to validate coverage.

### Understanding the output

**Success indicators:**
```text
[42/167] Fetching SBOM for owner/repo@1.2.3
  Saved dependency SBOM: .../owner_repo_1.2.3.json
```

**Rate limit handling:**
```text
2025-11-19 12:34:56 - WARNING - Approaching rate limit (4 remaining), will wait 120 seconds after next request
2025-11-19 12:34:58 - WARNING - SBOM request for owner/repo returned 429 (attempt 1/3): Rate limit exceeded. Retrying in 120.0s...
```

**Automatic retry:**
```text
2025-11-19 12:35:01 - WARNING - SBOM request for owner/repo returned 500 (attempt 1/3): Server error. Retrying in 2.0s...
2025-11-19 12:35:03 - WARNING - SBOM request for owner/repo returned 500 (attempt 2/3): Server error. Retrying in 4.0s...
2025-11-19 12:35:07 - INFO - Saved dependency SBOM: .../owner_repo_1.2.3.json
```

**Resume skip:**
```text
[42/167] Skipping owner/repo@1.2.3 (already completed)
```
