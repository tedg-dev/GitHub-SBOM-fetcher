# Mapper Investigation - Packages Not Being Mapped

## Issue Report

User found that several packages reported as "unmapped" actually DO have GitHub repositories:

### Packages Incorrectly Reported as Unmapped

1. **boolbase** (v1.0.0)
   - **Actual Repo**: https://github.com/fb55/boolbase
   - **Status**: Has repo, but "No dependencies found" in GitHub Dependency Graph
   - **Currently**: Listed as unmapped

2. **eyes** (v0.1.8)
   - **Actual Repo**: https://github.com/cloudhead/eyes.js
   - **Status**: Has repo, but "No dependencies found" in GitHub Dependency Graph
   - **Currently**: Listed as unmapped

3. **@ffmpeg-installer/ffmpeg** (v1.0.13)
   - **Actual Repo**: https://github.com/kribblo/node-ffmpeg-installer
   - **Status**: Has repo with **216 dependencies** in SBOM!
   - **Currently**: Listed as unmapped ❌ (CRITICAL)

4. **@ffmpeg-installer/win32-x64** (v4.0.2)
   - **Actual Repo**: https://github.com/cdytharuajay123-afk/Universal-video-Downloader
   - **Status**: Has repo with **244 dependencies** in SBOM!
   - **Currently**: Listed as unmapped ❌ (CRITICAL)

### Packages Correctly Unmapped

These packages do NOT have GitHub links in the Dependency Graph UI:

5. **@ffmpeg-installer/darwin-x64** (v4.0.4)
   - Transitive dependency via npm · package-lock.json
   - No GitHub link in UI ✅ Correctly unmapped

6. **@ffmpeg-installer/linux-ia32** (v4.0.3)
   - Transitive dependency via npm · package-lock.json
   - No GitHub link in UI ✅ Correctly unmapped

7. **@ffmpeg-installer/linux-x64** (v4.0.3)
   - Transitive dependency via npm · package-lock.json
   - No GitHub link in UI ✅ Correctly unmapped

8. **@ffmpeg-installer/win32-ia32** (v4.0.3)
   - Transitive dependency via npm · package-lock.json
   - No GitHub link in UI ✅ Correctly unmapped

## Impact Analysis

### Current State
- **Total "unmapped"**: 7 packages
- **Actually have GitHub repos**: 4 packages (57%!)
- **Actually have SBOMs**: 2 packages (@ffmpeg-installer/ffmpeg, @ffmpeg-installer/win32-x64)
- **Missing SBOMs**: 216 + 244 = **460 transitive dependencies!**

### Critical Issues

1. **@ffmpeg-installer/ffmpeg** has **216 dependencies** we're not fetching
2. **@ffmpeg-installer/win32-x64** has **244 dependencies** we're not fetching
3. Total missing: **~460 transitive dependencies** from just 2 packages

## Root Cause Hypothesis

### NPM Mapper Logic Issue

**File**: `src/sbom_fetcher/services/mappers.py`

The `NPMPackageMapper.map_to_github()` method:
1. Fetches package metadata from npm registry
2. Extracts `repository` field
3. Parses GitHub URL

**Potential Issues**:

1. **Line 55**: `repo_info = data.get("repository", {})`
   - If npm returns `"repository": null`, the default `{}` won't apply
   - Would get `None` instead, causing downstream issues

2. **Scoped Package Handling** (@ffmpeg-installer/*)
   - npm registry URL encoding for scoped packages
   - Might need URL encoding: `@ffmpeg-installer/ffmpeg` → `%40ffmpeg-installer%2Fffmpeg`

3. **Repository Field Variations**
   - Some packages have incomplete metadata
   - Some use shorthand format: `"repository": "owner/repo"` instead of full URL

4. **Rate Limiting / Timeouts**
   - npm registry API might be rate limiting requests
   - Timeout of 10 seconds might be too short for batch requests

5. **Error Handling Too Broad**
   - Line 99-101: Catches all exceptions silently
   - Only logs at debug level
   - Can't diagnose actual failures

## Investigation Plan

### Step 1: Test npm Registry API Directly

Check what npm registry returns for these packages:
```bash
curl "https://registry.npmjs.org/boolbase"
curl "https://registry.npmjs.org/eyes"
curl "https://registry.npmjs.org/@ffmpeg-installer/ffmpeg"
curl "https://registry.npmjs.org/@ffmpeg-installer/win32-x64"
```

### Step 2: Check URL Encoding

Scoped packages might need encoding:
```python
# Current
url = f"{self._config.npm_registry_url}/{package_name}"

# Might need
from urllib.parse import quote
url = f"{self._config.npm_registry_url}/{quote(package_name, safe='')}"
```

### Step 3: Enhanced Error Logging

Add temporary debug logging to see actual API responses:
```python
logger.info("Fetching npm package: %s", package_name)
logger.info("npm API URL: %s", url)
logger.info("Response status: %d", resp.status_code)
if resp.status_code == 200:
    logger.info("Repository field: %s", repo_info)
```

### Step 4: Handle Repository Field Variations

```python
# Handle None explicitly
repo_info = data.get("repository")
if repo_info is None:
    return None

# Handle shorthand format
if isinstance(repo_info, str) and "/" in repo_info and "://" not in repo_info:
    # Shorthand format: "owner/repo"
    parts = repo_info.split("/")
    if len(parts) == 2:
        return GitHubRepository(owner=parts[0], repo=parts[1])
```

## Recommended Fix Priority

### High Priority (Critical - Missing 460 deps)
1. Fix scoped package handling (@ffmpeg-installer/*)
2. Test and validate URL encoding
3. Add better error logging to diagnose failures

### Medium Priority (Missing repos but no deps)
4. Handle `null` repository field explicitly
5. Add support for shorthand repository format

### Low Priority (Already no deps available)
6. Document that some packages have repos but no dependency graphs
7. Differentiate in report: "No repo" vs "Repo exists but no SBOM"

## Expected Outcome After Fix

### Current (Broken)
```
Unmapped packages: 7
- boolbase (npm) v1.0.0
- eyes (npm) v0.1.8
- @ffmpeg-installer/ffmpeg (npm) v1.0.13    ← MISSING 216 deps!
- @ffmpeg-installer/win32-x64 (npm) v4.0.2  ← MISSING 244 deps!
- @ffmpeg-installer/darwin-x64 (npm) v4.0.4
- @ffmpeg-installer/linux-x64 (npm) v4.0.3
- @ffmpeg-installer/linux-ia32 (npm) v4.0.3
```

### After Fix (Expected)
```
Unmapped packages: 4
- @ffmpeg-installer/darwin-x64 (npm) v4.0.4  ✓ No GitHub repo
- @ffmpeg-installer/linux-x64 (npm) v4.0.3   ✓ No GitHub repo
- @ffmpeg-installer/linux-ia32 (npm) v4.0.3  ✓ No GitHub repo
- @ffmpeg-installer/win32-ia32 (npm) v4.0.3  ✓ No GitHub repo

Successfully mapped (but no SBOM available):
- boolbase → fb55/boolbase (no dependency graph)
- eyes → cloudhead/eyes.js (no dependency graph)

Successfully mapped AND fetched SBOMs:
- @ffmpeg-installer/ffmpeg → kribblo/node-ffmpeg-installer (216 deps)
- @ffmpeg-installer/win32-x64 → cdytharuajay123-afk/Universal-video-Downloader (244 deps)
```

## Testing Strategy

1. **Unit Test**: Create test for scoped package parsing
2. **Integration Test**: Run against tedg-dev/beatBot again
3. **Validation**: Verify all 4 packages now map correctly
4. **SBOM Count**: Should increase from 164 to 166 downloaded SBOMs

## Files to Modify

1. **`src/sbom_fetcher/services/mappers.py`**
   - Fix scoped package URL handling
   - Handle null/shorthand repository formats
   - Improve error logging

2. **Tests** (if needed)
   - Add test for scoped packages
   - Add test for various repository field formats

## Documentation Updates Needed

After fix, update:
1. `UNMAPPED_PACKAGES_LISTING.md` - Reflect actual unmapped count
2. Execution report - Show correct breakdown
3. Add note about packages with repos but no dependency graphs

---

**Status**: 🔴 **CRITICAL ISSUE IDENTIFIED**  
**Priority**: **HIGH** (Missing 460+ transitive dependencies)  
**Next Action**: Investigate npm registry API responses for failing packages  
**Expected Fix**: URL encoding for scoped packages + null handling
