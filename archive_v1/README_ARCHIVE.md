# Archive - Original Implementation (v1)

This directory contains the original procedural implementation of the SBOM Fetcher before the v2.0 production-grade refactoring.

## 📁 Contents

### Main Scripts
- **`github_sbom_api_fetcher.py`** - Original API-based SBOM fetcher (984 LOC)
  - The base script that was refactored into v2.0
  - 93% test coverage with 90 tests
  - Procedural design with functions

- **`fetch_sbom_hierarchy.py`** - Hierarchical SBOM fetcher
- **`fetch_sbom.py`** - Basic SBOM fetcher
- **`github_sbom_scraper.py`** - Web scraper version

### Tests
- **`tests/`** - Complete test suite (90 tests, 93% coverage)
  - `test_github_sbom_api_fetcher.py`
  - `test_github_sbom_api_fetcher_extended.py`
  - `test_github_sbom_api_fetcher_comprehensive.py`
  - `test_main_integration.py`
  - Other test files

### Documentation
- **Analysis Documents**:
  - `API_APPROACH_RECOMMENDATION.md`
  - `API_VS_SCRAPER_RESULTS.md`
  - `DEDUPLICATION_RECOMMENDATION.md`
  - `DEDUPLICATION_RESULTS.md`
  - `SBOM_VERSION_LIMITATION_ANALYSIS.md`
  
- **Progress Reports**:
  - `TEST_COVERAGE_REPORT.md`
  - `ENHANCEMENT_SUMMARY.md`
  - `UPGRADE_SUMMARY.md`

### Configuration
- `setup_environment.sh` - Original setup script
- `pytest.ini` - Original pytest configuration
- `requirements-dev.txt` - Original dev dependencies
- `setup.py` - Original setup script

### Output Data
- `sboms/` - Sample SBOM outputs
- `sboms_1pm/` - Time-stamped SBOM outputs
- `sboms_api/` - API-fetched SBOM outputs
- `htmlcov/` - Coverage reports
- `debug_output/` - Debug artifacts

## 🔄 Migration to v2.0

The v2.0 production refactoring transformed this codebase into a layered architecture:

| Original | Refactored v2.0 |
|----------|-----------------|
| Procedural functions | Class-based with DI |
| Single 984 LOC file | 19 modules, 2732 LOC |
| No design patterns | 7+ design patterns |
| Global state | Pure functions |
| Manual testing | Protocol-based mocking |

### Function Mapping

```python
# v1 (procedural)
fetch_root_sbom(session, owner, repo)

# v2 (class-based with DI)
class GitHubClient:
    def fetch_root_sbom(self, owner: str, repo: str)
```

See `REFACTORING_COMPLETE.md` in the project root for full details.

## 🧪 Running Original Code

```bash
# Setup v1 environment
source venv/bin/activate
pip install requests pytest pytest-cov

# Run original script
python github_sbom_api_fetcher.py --gh-user tedg-dev --gh-repo beatBot

# Run original tests
pytest tests/ -v
```

## 📊 Original Test Coverage

The original implementation achieved:
- **93% code coverage**
- **90 passing tests**
- Full workflow coverage
- Edge case testing
- Failure scenario testing

All tests can be adapted to v2.0 by updating imports and mocking strategies.

## 🗄️ Preservation Notice

This archive is preserved for:
1. **Historical reference** - Document the evolution of the codebase
2. **Test compatibility** - Original tests can be adapted for v2.0
3. **Rollback option** - If needed, this version is fully functional
4. **Learning resource** - Compare procedural vs. architectural approaches

## ⚠️ Deprecated

This code is **archived** and no longer actively maintained. Use the v2.0 implementation in the project root (`src/sbom_fetcher/`) for all new work.

---

*Archived on: December 3, 2025*  
*Original coverage: 93%*  
*Total LOC: ~1000*  
*Refactored to: v2.0 (2732 LOC, layered architecture)*
