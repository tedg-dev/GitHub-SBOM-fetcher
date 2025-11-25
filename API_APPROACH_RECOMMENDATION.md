# API-Based SBOM Dependency Fetcher - Technical Recommendation

## Problem with Current Approach (HTML Scraping)
- **Volatile**: GitHub can change HTML structure at any time
- **Private repos**: Dependency graph web UI often disabled/inaccessible
- **Incomplete**: JavaScript-rendered content not captured (~3% missing)
- **Fragile**: Requires complex parsing logic that breaks easily

## Recommended API-Based Approach

### Core Discovery: GitHub SBOM API Contains Everything!

The GitHub Dependency Graph SBOM API (`/repos/{owner}/{repo}/dependency-graph/sbom`) already includes:
- ✅ **All dependencies** (230 packages vs 223 from scraping for beatBot!)
- ✅ **Package versions** (exact versions used)
- ✅ **Package URLs** (purls like `pkg:npm/lodash@4.17.5`)
- ✅ **Dependency relationships** (DEPENDS_ON relationships)
- ✅ **Works for private repos** (if dependency graph enabled)
- ✅ **Stable SPDX format** (industry standard, won't change)

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Get Root SBOM via API                              │
│  GET /repos/{owner}/{repo}/dependency-graph/sbom            │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Parse SBOM (SPDX 2.3 format)                      │
│  - Extract all packages from sbom.packages[]                │
│  - Get Package URLs (purls) from externalRefs               │
│  - Parse relationships for dependency tree                  │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Map Packages to GitHub Repositories               │
│  For each package:                                          │
│  - npm packages: Query npm registry API                    │
│    GET https://registry.npmjs.org/{package}                │
│  - PyPI packages: Query PyPI API                           │
│    GET https://pypi.org/pypi/{package}/json                │
│  - Extract GitHub repo from repository.url field           │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Download SBOMs for Each Dependency                │
│  For each mapped GitHub repo:                              │
│  GET /repos/{owner}/{repo}/dependency-graph/sbom           │
│  - Save with package name + version                        │
│  - Track successes/failures                                │
└─────────────────────────────────────────────────────────────┘
```

### Key Advantages

1. **More Complete** (230 vs 223 packages for beatBot)
   - Gets everything GitHub dependency graph knows about
   - No JavaScript rendering issues
   
2. **Stable APIs**
   - GitHub SBOM API: Documented, versioned, supported
   - npm/PyPI registry APIs: Stable, well-documented
   - SPDX format: Industry standard (Linux Foundation)

3. **Works for Private Repos**
   - No HTML scraping needed
   - Just needs API access (same token)

4. **Better Package Info**
   - Exact versions used (not just what's on HTML page)
   - Dependency relationships (which package depends on what)
   - Package URLs (standard identifiers)

5. **Faster & More Reliable**
   - No HTML parsing overhead
   - Direct API calls
   - Structured JSON responses

### Implementation Details

#### Package URL (purl) Format
```
pkg:npm/graceful-fs@4.1.11
pkg:pypi/django@3.2.0
pkg:maven/org.apache.commons/commons-lang3@3.12.0
```

#### npm Registry API Response
```json
{
  "name": "lodash",
  "version": "4.17.21",
  "repository": {
    "type": "git",
    "url": "git+https://github.com/lodash/lodash.git"
  }
}
```

#### PyPI API Response
```json
{
  "info": {
    "name": "requests",
    "version": "2.28.0",
    "project_urls": {
      "Homepage": "https://requests.readthedocs.io",
      "Source": "https://github.com/psf/requests"
    }
  }
}
```

### Edge Cases to Handle

1. **Packages without GitHub repos**
   - Some npm packages don't have public GitHub repos
   - Log these separately (like current scraper does)

2. **Monorepo packages**
   - Multiple npm packages from one GitHub repo
   - May have different SBOMs or same SBOM

3. **Package name mismatches**
   - npm package name ≠ GitHub repo name
   - Use registry API mapping (most reliable)

4. **Private dependencies**
   - May not have public repos
   - May require additional auth

5. **Rate limiting**
   - GitHub API: 5000/hour authenticated
   - npm registry: No strict limit but be respectful
   - PyPI: No strict limit

### Performance Comparison

| Metric | HTML Scraper | API Approach |
|--------|-------------|--------------|
| beatBot dependencies found | 223 | **230** ✅ |
| Private repo support | ❌ (web UI disabled) | ✅ (API works) |
| Stability | Low (HTML changes) | High (versioned APIs) |
| Speed | Slow (HTML parsing) | Fast (JSON APIs) |
| Maintenance | High (brittle) | Low (stable APIs) |

### Recommended Libraries

1. **packageurl-python** - Parse and handle Package URLs (purls)
   ```bash
   pip install packageurl-python
   ```

2. **requests** - Already installed, for API calls

3. **spdx-tools** (optional) - Official SPDX parsing if needed
   ```bash
   pip install spdx-tools
   ```

### File Structure (Proposed)

```
github_sbom_api_fetcher.py          # New API-based implementation
├── Dependency dataclass
├── parse_sbom()                    # Parse SPDX SBOM
├── extract_packages()              # Get packages from SBOM
├── map_package_to_github()         # npm/PyPI → GitHub
├── fetch_dependency_sboms()        # Download all SBOMs
└── main()                          # Orchestration

API_APPROACH_RECOMMENDATION.md      # This document
```

### Migration Path

1. **Phase 1**: Implement API-based fetcher alongside scraper
2. **Phase 2**: Test on beatBot and other repos
3. **Phase 3**: Compare results (should get ≥ scraper results)
4. **Phase 4**: Make API fetcher the default
5. **Phase 5**: Keep scraper as fallback for edge cases

### Success Criteria

- ✅ Find ≥ 230 dependencies for beatBot (vs 223 with scraper)
- ✅ Download ≥ 166 SBOMs (match or exceed scraper)
- ✅ Work for private repos (unlike scraper)
- ✅ No HTML parsing fragility
- ✅ Faster execution time

## Next Steps

1. Implement `github_sbom_api_fetcher.py`
2. Add npm/PyPI registry mapping logic
3. Test on beatBot (should find 230 packages)
4. Test on xplat_fileshare (should work for private repo)
5. Compare results with scraper
6. Add comprehensive error handling
7. Update documentation

## Conclusion

The API-based approach is **superior in every way**:
- More dependencies found (230 vs 223)
- Works for private repos
- Stable and maintainable
- Faster and more reliable
- Industry-standard formats

This should be the **new primary tool**, with the HTML scraper kept only as a historical reference or extreme fallback.
