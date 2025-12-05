# Debug Mapping Guide - Generic Solution for Any Repository

## Overview

The mapper now has **comprehensive debug logging** that works with **any GitHub repository**. This helps diagnose why packages fail to map to their GitHub repositories.

## How to Use

### Run with Debug Logging

```bash
python -m sbom_fetcher --gh-user OWNER --gh-repo REPO --debug
```

Example:
```bash
python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --debug
```

### What Gets Logged

The mapper logs **every decision point** for **every package**:

#### 1. npm Registry Response
```
DEBUG: npm registry returned 404 for package-name
```
- Means: Package not found in npm registry
- Common for: Typos, private packages, deleted packages

#### 2. Missing Repository Field
```
DEBUG: Package package-name has no repository field (null)
```
- Means: npm returned `"repository": null`
- Common for: Old packages, packages without metadata

#### 3. Empty Repository URL
```
DEBUG: Package package-name has empty repository URL
```
- Means: Repository field exists but URL is empty
- Common for: Malformed package metadata

#### 4. Non-GitHub Repository
```
DEBUG: Package package-name repository is not GitHub: https://gitlab.com/owner/repo
```
- Means: Package is hosted on GitLab, Bitbucket, etc.
- Expected: Tool only works with GitHub repos

#### 5. Successful Mapping
```
DEBUG: Successfully mapped package-name → owner/repo
```
- Means: Package successfully mapped to GitHub repository
- Will proceed to download SBOM

#### 6. Path Parsing Failure
```
DEBUG: Package package-name: Could not extract owner/repo from path: some/invalid/path
```
- Means: URL parsed but couldn't extract owner/repo
- Common for: Unusual URL formats

#### 7. Exceptions
```
DEBUG: Error mapping npm package package-name: error details
```
- Means: Unexpected error during mapping
- Helps: Identify bugs or edge cases

## Example Debug Output

### Successful Mapping
```
2025-12-05 08:00:00 - DEBUG - Successfully mapped @ffmpeg-installer/ffmpeg → kribblo/node-ffmpeg-installer
```

### Failed Mapping (No Repo Field)
```
2025-12-05 08:00:01 - DEBUG - Package boolbase has no repository field (null)
```

### Failed Mapping (Non-GitHub)
```
2025-12-05 08:00:02 - DEBUG - Package some-package repository is not GitHub: https://bitbucket.org/user/repo
```

## Analyzing Results

### Step 1: Run with Debug

```bash
python -m sbom_fetcher --gh-user OWNER --gh-repo REPO --debug 2>&1 | tee debug_run.log
```

### Step 2: Filter for Unmapped Packages

```bash
# See all debug messages for unmapped packages
grep "DEBUG.*has no repository" debug_run.log

# See all non-GitHub repositories
grep "DEBUG.*not GitHub" debug_run.log

# See all successfully mapped packages
grep "DEBUG.*Successfully mapped" debug_run.log
```

### Step 3: Identify Patterns

Look for common issues:
- **Many "has no repository field"**: Old/unmaintained packages
- **Many "not GitHub"**: Packages hosted elsewhere (expected)
- **Few "Successfully mapped"**: Possible systematic issue

## Generic Solutions Based on Debug Output

### Issue: "has no repository field (null)"

**Cause**: npm package metadata doesn't include repository  
**Solution**: Cannot map - package metadata is incomplete  
**Status**: Expected for old/unmaintained packages

### Issue: "repository is not GitHub"

**Cause**: Package hosted on GitLab, Bitbucket, etc.  
**Solution**: Cannot map - tool only works with GitHub  
**Status**: Expected, correctly excluded

### Issue: "Could not extract owner/repo from path"

**Cause**: Repository URL format not recognized  
**Action**: May need to enhance URL parser (generic fix)

### Issue: npm registry returned 404

**Cause**: Package name mismatch or package doesn't exist  
**Action**: Check if PURL → package name conversion is correct

## Common Mapping Scenarios

### Scenario 1: Scoped Package (@org/pkg)

```
Input: @ffmpeg-installer/ffmpeg
URL Encoding: %40ffmpeg-installer%2Fffmpeg
npm URL: https://registry.npmjs.org/%40ffmpeg-installer%2Fffmpeg
Result: Successfully mapped
```

### Scenario 2: Package Without Metadata

```
Input: old-package
npm Response: {"repository": null}
Debug Log: "Package old-package has no repository field (null)"
Result: Unmapped (expected)
```

### Scenario 3: Non-GitHub Package

```
Input: gitlab-package
npm Response: {"repository": "https://gitlab.com/user/repo"}
Debug Log: "Package gitlab-package repository is not GitHub: https://gitlab.com/user/repo"
Result: Unmapped (expected)
```

### Scenario 4: Platform-Specific Binary

```
Input: @ffmpeg-installer/darwin-x64
npm Response: {"repository": null} or missing
Debug Log: "Package @ffmpeg-installer/darwin-x64 has no repository field (null)"
Result: Unmapped (expected - no source repo)
```

## Troubleshooting Any Repository

### Step 1: Run with Debug
```bash
python -m sbom_fetcher --gh-user USER --gh-repo REPO --debug > output.log 2>&1
```

### Step 2: Check Unmapped Packages
```bash
grep "Unmapped packages:" output.log -A 20
```

### Step 3: Find Debug Info for Each
```bash
grep "DEBUG.*package-name" output.log
```

### Step 4: Categorize Issues

Create categories:
- **No repo metadata**: Expected, cannot fix
- **Non-GitHub**: Expected, cannot fix
- **Parse failure**: Needs generic enhancement
- **Network error**: Transient, retry
- **Unknown error**: Investigation needed

## Enhancing the Mapper (Generic Approach)

If debug logs show a **pattern** of parse failures:

### 1. Identify the URL Format
```
DEBUG: Package xyz: Could not extract owner/repo from path: unusual/format/here
```

### 2. Add Generic Handler

```python
# In mappers.py, add new URL format handler
if some_pattern_match(repo_url):
    # Extract owner/repo using new pattern
    return GitHubRepository(owner=..., repo=...)
```

### 3. Test Generically

Ensure fix works for:
- Multiple packages with same issue
- Different repositories
- Edge cases

## Benefits of This Approach

1. **Generic**: Works with any GitHub repository
2. **Diagnostic**: Shows exactly why each package fails
3. **No Hardcoding**: Doesn't target specific packages
4. **Maintainable**: Easy to identify systematic issues
5. **Extensible**: Debug info guides generic enhancements

## Next Steps After Debug Run

### If Many Packages Have Same Issue

1. **Document the pattern** in the debug log
2. **Identify root cause** (URL format, metadata format, etc.)
3. **Implement generic fix** that handles the pattern
4. **Test with multiple repositories** to ensure generality

### If Issues Are Package-Specific

1. **Accept as expected** (old packages, non-GitHub, etc.)
2. **Document in unmapped packages section** of report
3. **Explain why** (no metadata, not on GitHub, etc.)

## Summary

The debug logging provides **complete visibility** into the mapping process for **any GitHub repository**:

- ✅ Works generically with all repositories
- ✅ Shows exact failure reason for each package
- ✅ Helps identify systematic issues
- ✅ Guides generic enhancements
- ✅ No package-specific hardcoding

**Usage**: Simply add `--debug` flag when running the tool on **any repository**.

---

**Created**: December 5, 2025  
**Purpose**: Generic debugging for any GitHub repository  
**File**: `src/sbom_fetcher/services/mappers.py`
