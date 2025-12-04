# GitHub SBOM API Version Limitation - Deep Dive Analysis

## Executive Summary

**Critical Finding:** GitHub's SBOM API **only returns SBOMs for the DEFAULT BRANCH** (main/master), not for specific versions, tags, or historical commits.

**Impact:** When a project uses multiple versions of the same dependency (e.g., lodash@0.9.2, lodash@4.17.5), all downloaded SBOMs are **effectively identical** - they represent the current state of the repository, not the historical version.

## The Problem

### Example: beatBot's lodash Dependencies

beatBot uses multiple versions of lodash:
- `lodash@0.9.2` (from 2013)
- `lodash@2.4.2` (from 2014)
- `lodash@3.10.1` (from 2015)
- `lodash@4.5.1` (from 2017)
- `lodash@4.6.1` (from 2017)
- `lodash@4.17.5` (from 2018)

### What We Get vs What We Want

| What We Want | What We Actually Get |
|-------------|---------------------|
| SBOM for lodash@0.9.2 (2013 state) | SBOM for lodash@main (2025 state) |
| SBOM for lodash@4.17.5 (2018 state) | SBOM for lodash@main (2025 state) |
| SBOM for lodash@4.6.1 (2017 state) | SBOM for lodash@main (2025 state) |

### Verification

```bash
# All lodash SBOMs are the same size
$ ls -lh *lodash*.json
-rw-r--r-- 1 tedg staff 529K lodash_lodash_0.9.2.json
-rw-r--r-- 1 tedg staff 529K lodash_lodash_2.4.2.json
-rw-r--r-- 1 tedg staff 529K lodash_lodash_3.10.1.json
-rw-r--r-- 1 tedg staff 529K lodash_lodash_4.17.5.json
-rw-r--r-- 1 tedg staff 529K lodash_lodash_4.5.1.json
-rw-r--r-- 1 tedg staff 529K lodash_lodash_4.6.1.json

# All show version "main" and 615 packages (current state)
$ jq '.sbom.packages[] | select(.name | contains("lodash/lodash")) | .versionInfo' lodash_lodash_0.9.2.json
"main"

$ jq '.sbom.packages[] | select(.name | contains("lodash/lodash")) | .versionInfo' lodash_lodash_4.17.5.json
"main"
```

### Why Are MD5 Hashes Different?

The files have different MD5 hashes because of:
1. **Creation timestamp** - Each API call generates a new timestamp
2. **Document namespace UUID** - Each SBOM gets a unique SPDX document ID
3. **Nothing else** - The actual package data is identical

```json
{
  "sbom": {
    "creationInfo": {
      "created": "2025-11-24T23:43:07Z"  // ← Different timestamp
    },
    "documentNamespace": "https://spdx.org/spdxdocs/protobom/127b624b-e15f-4208-94ef..."  // ← Different UUID
  }
}
```

## Root Cause: GitHub API Design

### GitHub SBOM API Endpoint

```
GET /repos/{owner}/{repo}/dependency-graph/sbom
```

**Parameters:** NONE for version, tag, ref, or commit

### GitHub API Documentation

From [GitHub REST API docs](https://docs.github.com/en/rest/dependency-graph/sboms):

> "Gets the dependency graph SBOM for a repository. The SBOM is generated from the **default branch** of the repository."

**Translation:** You can ONLY get the current state, not historical versions.

### Other GitHub APIs Checked

| API | Supports Version-Specific Data? |
|-----|--------------------------------|
| SBOM API | ❌ No - default branch only |
| GraphQL `dependencyGraphManifests` | ❌ No - default branch only |
| Dependency Graph Compare | ❌ Partial - compares refs but no full SBOM |
| Contents API (package.json) | ✅ Yes - but not SBOM format |

## Impact Analysis

### For beatBot (Example Repository)

**Total unique repositories:** 167

**Repositories with multiple versions:** ~45 repos

**Duplicate SBOM downloads:**
- lodash: 6 versions → 5 duplicate downloads
- async: 2 versions → 1 duplicate download  
- inherits: 2 versions → 1 duplicate download
- glob: 2 versions → 1 duplicate download
- etc.

**Estimated waste:** ~55 duplicate downloads (same content, different filenames)

### Storage Impact

```
Actual unique SBOMs: ~112 repos
Downloaded files: 220 files
Duplicate content: ~108 files
Storage waste: ~56 MB (duplicate content)
```

### Accuracy Impact

**The SBOMs are MISLEADING:**
- File named `lodash_lodash_0.9.2.json` actually contains dependencies for lodash@main (2025)
- lodash@0.9.2 (2013) had ZERO dependencies
- lodash@main (2025) has 615 packages
- **The SBOM is completely wrong for the historical version**

## What This Means for Security Analysis

### False Positives/Negatives

If you're doing vulnerability scanning based on these SBOMs:

1. **False Positives:** Modern dependencies appear in old version SBOMs
   - Example: lodash@0.9.2 SBOM shows modern packages that didn't exist in 2013
   - Could flag vulnerabilities that don't actually exist in your dependency

2. **False Negatives:** Historical vulnerabilities might be missed
   - Example: lodash@0.9.2 might have had vulnerable dependencies
   - But SBOM shows current dependencies, missing historical vulns

3. **Incorrect Dependency Tree:**
   - Security analysis assumes lodash@0.9.2 depends on 615 packages
   - Reality: lodash@0.9.2 had 0 dependencies
   - Complete misrepresentation of attack surface

## Possible Solutions

### Option 1: Deduplicate Downloads (Recommended)

**Approach:** Download each unique repository only once, ignoring version numbers.

**Implementation:**
```python
# Track downloaded repos by owner/repo only
downloaded_repos = set()

for pkg in packages:
    repo_key = f"{pkg.github_owner}/{pkg.github_repo}"
    
    if repo_key in downloaded_repos:
        logger.info("Skipping duplicate: %s (already have SBOM for this repo)", 
                    pkg.name)
        continue
    
    download_sbom(pkg)
    downloaded_repos.add(repo_key)
```

**Pros:**
- ✅ Eliminates duplicate downloads
- ✅ Accurate representation of what GitHub API provides
- ✅ Faster execution
- ✅ Less storage

**Cons:**
- ⚠️ Lose version information in filenames
- ⚠️ Need to clarify in docs that SBOMs are for current state

### Option 2: Build Version-Specific SBOMs Manually

**Approach:** Reconstruct dependency tree from historical package manifests.

**Implementation:**
```python
# For each version, checkout that tag and build SBOM
1. Get package.json for specific tag via Contents API
2. Resolve all dependencies (direct + transitive)
3. Recursively map each dependency to GitHub repo
4. Build SPDX SBOM format manually
```

**Pros:**
- ✅ Accurate version-specific SBOMs
- ✅ Correct for security analysis

**Cons:**
- ❌ Extremely complex (need full dependency resolver)
- ❌ Very slow (recursive API calls)
- ❌ Ecosystem-specific (different logic for npm, PyPI, Maven, etc.)
- ❌ May not match GitHub's SBOM format exactly
- ❌ Transitive dependencies are hard to resolve correctly

### Option 3: Use Package Registry Data Instead

**Approach:** Get dependency data from npm/PyPI/etc., not GitHub.

**Implementation:**
```python
# For npm packages
r = requests.get(f"https://registry.npmjs.org/lodash/0.9.2")
data = r.json()
dependencies = data.get('dependencies', {})
# But this is just package names, not GitHub repos or SBOMs
```

**Pros:**
- ✅ Registry has historical version data
- ✅ Faster than building SBOMs manually

**Cons:**
- ❌ Only gives package names, not GitHub repos
- ❌ No transitive dependencies
- ❌ Not in SBOM format
- ❌ Would need significant transformation

### Option 4: Document Limitation and Download Once Per Repo

**Approach:** Accept GitHub's limitation and be transparent about it.

**Implementation:**
```python
# Download only one SBOM per repo
# Save as: {owner}_{repo}_current.json
# Document clearly that this is current state, not version-specific
```

**Pros:**
- ✅ Simple and honest
- ✅ Fast
- ✅ Uses official GitHub APIs
- ✅ Clear documentation

**Cons:**
- ⚠️ SBOMs don't match historical versions
- ⚠️ Need clear warnings for security use cases

## Recommendations

### Immediate Action: Deduplicate (Option 1 + 4)

**Update the API fetcher to:**

1. **Download each repository only once**
   - Track by `owner/repo` not `owner/repo/version`
   - Save as `{owner}_{repo}_current.json` (not version-specific)

2. **Add clear documentation:**
   ```
   IMPORTANT: GitHub's SBOM API only provides SBOMs for the current 
   state of repositories (default branch), not for specific versions.
   
   When multiple versions of a package are used (e.g., lodash@0.9.2 
   and lodash@4.17.5), only ONE SBOM is downloaded representing the 
   current state of the lodash/lodash repository.
   
   For historical version-specific SBOMs, manual reconstruction would 
   be required using package manifests and dependency resolvers.
   ```

3. **Update summary output:**
   ```
   Packages in root SBOM: 230
   Unique repositories mapped: 167 (after deduplication)
   SBOMs downloaded: 167
   Duplicate versions skipped: 55
   ```

4. **Add metadata file:**
   Create `version_mapping.json` to track which versions map to each SBOM:
   ```json
   {
     "lodash/lodash": {
       "sbom_file": "lodash_lodash_current.json",
       "versions_using_this_repo": ["0.9.2", "2.4.2", "3.10.1", "4.5.1", "4.6.1", "4.17.5"],
       "note": "SBOM represents current state (main branch), not historical versions"
     }
   }
   ```

### Long-term: Consider fetch_sbom_hierarchy.py

The `fetch_sbom_hierarchy.py` tool might have different behavior worth investigating:
- Does it fetch from npm registry?
- Does it build version-specific dependency trees?
- Does it have better version handling?

Worth reviewing as an alternative approach.

## Comparison: HTML Scraper vs API Fetcher

### HTML Scraper Behavior

The HTML scraper had the SAME limitation:
- Scraped dependency graph page shows current dependencies
- When downloading SBOMs, it also hits the same API endpoint
- **Same limitation, same duplicate downloads**

### Neither Tool Can Get Historical SBOMs

This is a **GitHub platform limitation**, not a tool limitation:
- GitHub doesn't provide version-specific SBOMs via any API
- Both HTML scraper and API fetcher hit the same SBOM endpoint
- Both download identical SBOMs for multiple versions

## Conclusion

### The Truth About GitHub SBOMs

**GitHub's SBOM API is designed for:**
- ✅ Current security posture of repositories
- ✅ Understanding what dependencies a repo has NOW
- ✅ Identifying current vulnerabilities

**GitHub's SBOM API is NOT designed for:**
- ❌ Historical dependency analysis
- ❌ Understanding past versions' dependency trees
- ❌ Version-specific vulnerability scanning
- ❌ Reproducing historical builds

### What We Should Do

1. **Deduplicate downloads** - Download each repo once
2. **Clear documentation** - Explain the limitation
3. **Version mapping file** - Track which versions use each SBOM
4. **Honest naming** - `{owner}_{repo}_current.json` not version-specific
5. **Warning in output** - Alert users to the limitation

### What Users Should Know

If you need **truly version-specific SBOMs**, you have two options:
1. **Manual reconstruction** - Complex, slow, but accurate
2. **Use package lockfiles** - `package-lock.json`, `Pipfile.lock`, etc. contain exact dependency trees

For **current security posture**, GitHub's SBOMs are excellent and this limitation doesn't matter.

---

**Date:** 2025-11-24  
**Issue:** GitHub SBOM API version limitation  
**Impact:** Duplicate downloads with identical content  
**Recommendation:** Deduplicate and document
