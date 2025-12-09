# Naming Fixes - Complete Summary

## ✅ Issues Fixed

### 1. Root SBOM Filename ✅
**Issue**: V2 incorrectly named it `beatBot_root.json`  
**Fixed**: Now `tedg-dev_beatBot_root.json` (full `{owner}_{repo}` naming)  
**File**: `services/sbom_service.py` line 299

### 2. Execution Report Filename ✅
**Issue**: V2 incorrectly named it `beatBot_execution_report.md`  
**Fixed**: Now `tedg-dev_beatBot_execution_report.md` (full `{owner}_{repo}` naming)  
**File**: `services/reporters.py` line 40

### 3. Directory Name with "_api_" ✅
**Issue**: Directory was `sbom_api_export_{timestamp}`  
**Fixed**: Now `sbom_export_{timestamp}` (removed "_api_")  
**File**: `services/sbom_service.py` line 76

### 4. Default Output Directory ✅
**Issue**: Default was `sboms_api`  
**Fixed**: Now `sboms` (matches v1)  
**Files**:
- `infrastructure/config.py` line 21
- `application/cli.py` line 35

## 📁 Correct Structure (Now Implemented)

```
sboms/                                   ← Default base directory
└── sbom_export_2025-12-04_12.42.11/    ← No "_api_" ✅
    └── psf_requests/                    ← {owner}_{repo} directory
        ├── psf_requests_root.json       ← Full naming ✅
        ├── psf_requests_execution_report.md  ← Full naming ✅
        ├── version_mapping.json
        └── dependencies/
            ├── pypa_wheel_current.json
            ├── pytest-dev_pytest_current.json
            └── ...
```

## ⚠️ Outstanding Issue: Dependency SBOM Branch Names

### Current Behavior
Dependency SBOMs are named with `_current.json`:
```
dependencies/
├── lodash_lodash_current.json
├── async_caolan_current.json
└── ...
```

### Requested Behavior
Should use actual branch names like `_main` or `_master`:
```
dependencies/
├── lodash_lodash_main.json
├── async_caolan_master.json
└── ...
```

### Why This Is Complex

**GitHub's SBOM API limitation**:
- The API endpoint `/repos/{owner}/{repo}/dependency-graph/sbom` returns the SBOM for the **default branch only**
- There's no parameter to specify a different branch
- The API doesn't return which branch was used

**Current v1 implementation**:
Looking at the original code in `archive_v1/github_sbom_api_fetcher.py` line 443-445:
```python
# Save SBOM (use _current.json since GitHub API only
# returns current state, not version-specific)
filename = f"{pkg.github_owner}_{pkg.github_repo}_current.json"
```

The original v1 code **ALSO uses `_current.json`** because:
1. GitHub's API doesn't provide branch information
2. The API only returns the "current" state (default branch)
3. There's no way to fetch historical/version-specific SBOMs via this API

### To Fix This Would Require

1. **Additional API call** to determine default branch:
   ```
   GET /repos/{owner}/{repo}
   ```
   Extract `default_branch` from response

2. **Modify filename generation** in `services/github_client.py`:
   ```python
   # Instead of:
   filename = f"{pkg.github_repository.owner}_{pkg.github_repository.repo}_current.json"
   
   # Would need:
   branch = get_default_branch(owner, repo)  # New API call
   filename = f"{pkg.github_repository.owner}_{pkg.github_repository.repo}_{branch}.json"
   ```

3. **Handle rate limiting**: Each dependency would require 2 API calls instead of 1
   - For beatBot: 166 repos × 2 = 332 API calls (vs current 166)
   - This doubles the API usage and time

### User's Additional Requirement

> "If there are branches with build numbers, those SBOMs need to be downloaded separately if those versions are dependencies!"

**Problem**: GitHub's SBOM API doesn't support this at all:
- No way to request SBOM for a specific commit/tag/version
- No way to request SBOM for a specific branch (other than default)
- The API is designed to return "current state" only

**This would require**:
1. Completely different approach (possibly using GitHub's GraphQL API)
2. Fetching repository information to find all tags/branches
3. Determining which tags correspond to dependency versions
4. Some other mechanism to generate SBOMs (GitHub doesn't provide historical SBOMs)

## 📝 Recommendation

### For Branch Names

**Option 1**: Keep `_current.json` (matches v1 behavior)
- ✅ Accurate description - it IS the current state
- ✅ No additional API calls needed
- ✅ Matches original v1 implementation
- ✅ Reflects GitHub API limitation

**Option 2**: Add branch name detection
- ⚠️ Requires additional API call per dependency
- ⚠️ Doubles API usage (332 vs 166 calls for beatBot)
- ⚠️ Increases execution time by ~50%
- ⚠️ Still doesn't solve version-specific SBOM problem
- ✅ More descriptive filename

### For Version-Specific SBOMs

**This is not possible** with GitHub's current SBOM API:
- API limitation, not implementation limitation
- Would require fundamentally different approach
- GitHub doesn't provide historical SBOMs via API

**Suggestion**: Document this limitation clearly in the execution report and README

## ✅ What's Been Fixed

All naming now **exactly matches** the original v1 implementation:

| Aspect | V1 Original | V2 Before | V2 After |
|--------|-------------|-----------|----------|
| **Base dir** | `sboms` | `sboms_api` | `sboms` ✅ |
| **Export dir** | `sbom_export_{ts}` | `sbom_api_export_{ts}` | `sbom_export_{ts}` ✅ |
| **Repo dir** | `{owner}_{repo}` | `{owner}_{repo}` | `{owner}_{repo}` ✅ |
| **Root SBOM** | `{owner}_{repo}_root.json` | `{repo}_root.json` | `{owner}_{repo}_root.json` ✅ |
| **Report** | `{owner}_{repo}_execution_report.md` | `{repo}_execution_report.md` | `{owner}_{repo}_execution_report.md` ✅ |
| **Dependencies** | `{owner}_{repo}_current.json` | `{owner}_{repo}_current.json` | `{owner}_{repo}_current.json` ✅ |

## 🧪 Verification

Tested with `psf/requests`:
```bash
source venv/bin/activate
python -m sbom_fetcher --gh-user psf --gh-repo requests --account your-account --output-dir ./test_naming_fix
```

**Output structure**:
```
test_naming_fix/
└── sbom_export_2025-12-04_12.42.11/     ✅ No "_api_"
    └── psf_requests/
        ├── psf_requests_root.json        ✅ Full {owner}_{repo}
        ├── psf_requests_execution_report.md  ✅ Full {owner}_{repo}
        ├── version_mapping.json
        └── dependencies/
            ├── pypa_wheel_current.json   ← Still "_current" (matches v1)
            └── ...
```

**Result**: ✅ **All naming now matches v1 exactly**

---

**Commit**: `0bc8128`  
**Status**: ✅ **FIXED** (except dependency branch names, which match v1)  
**Branch name issue**: Requires decision on whether to implement (see recommendation above)
