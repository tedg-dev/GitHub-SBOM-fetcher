# Code Coverage Requirements

**CRITICAL REQUIREMENT:** The SBOM Fetcher project must maintain code coverage at **97%+** for all future changes.

## 📊 Current Coverage Baseline (Locked In)

```
Coverage:     97.35%
Total Tests:  319 passing
Statements:   1020
Missed:       27 lines
```

### Module Coverage Breakdown

| Module | Coverage | Status |
|--------|----------|--------|
| application/main.py | 100% | ✅ |
| services/reporters.py | 100% | ✅ |
| domain/models.py | 100% | ✅ |
| domain/exceptions.py | 100% | ✅ |
| infrastructure/config.py | 100% | ✅ |
| infrastructure/filesystem.py | 100% | ✅ |
| infrastructure/http_client.py | 100% | ✅ |
| services/mapper_factory.py | 100% | ✅ |
| services/mappers.py | 97% | ✅ |
| services/sbom_service.py | 97% | ✅ |
| services/parsers.py | 96% | ✅ |
| services/github_client.py | 88% | ⚠️ |

## 🎯 Enforcement Rules

### For All Future Changes

#### ✅ Before Coding
1. Run baseline coverage:
   ```bash
   pytest tests/ --cov=src/sbom_fetcher
   ```
2. Note current coverage: **97.35%**

#### ✅ During Development
1. **Write tests FIRST** (Test-Driven Development)
2. Ensure new code has **95%+ coverage**
3. Cover edge cases and error paths
4. Test both success and failure scenarios

#### ✅ Before Committing
1. Run full test suite:
   ```bash
   pytest tests/ --cov=src/sbom_fetcher
   ```
2. Verify coverage >= **97%**
3. All tests must pass (319+ passing)
4. If coverage drops, add tests to restore it
5. Run code quality checks (black, isort, flake8)

#### ✅ In Pull Requests
- Coverage must be >= **97%**
- CI enforces **95% minimum** (will fail below)
- PRs should maintain or improve coverage
- Test quality reviewed alongside code
- Coverage report included in PR checks

## 📋 Quick Reference Commands

### Check Overall Coverage
```bash
pytest tests/ --cov=src/sbom_fetcher --cov-report=term-missing
```

### Generate HTML Report
```bash
pytest tests/ --cov=src/sbom_fetcher --cov-report=html
open htmlcov/index.html
```

### Check Specific Module
```bash
pytest tests/ --cov=src/sbom_fetcher/services/mappers.py --cov-report=term-missing
```

### Run Specific Test File
```bash
pytest tests/unit/services/test_mapper_edge_cases.py -v
```

### Run Tests with Verbose Output
```bash
pytest tests/ -v --cov=src/sbom_fetcher
```

### Check Coverage Summary Only
```bash
pytest tests/ --cov=src/sbom_fetcher --cov-report=term | tail -5
```

## ⚠️ What to Do If Coverage Drops

If coverage falls below 97%, follow these steps:

### 1. Identify Coverage Gaps
```bash
pytest --cov=src/sbom_fetcher --cov-report=term-missing | grep -E "^src.*%"
```

This will show all modules with their coverage and missing lines.

### 2. Find Specific Uncovered Lines
```bash
pytest --cov=src/sbom_fetcher --cov-report=term-missing
```

Look for lines marked with `!` or listed under "Missing" column.

### 3. Generate Detailed HTML Report
```bash
pytest tests/ --cov=src/sbom_fetcher --cov-report=html
open htmlcov/index.html
```

The HTML report highlights uncovered lines in red.

### 4. Add Targeted Tests
- Write tests specifically for uncovered lines
- Prioritize critical paths over logging/debug code
- Focus on behavior testing, not just coverage numbers
- Cover edge cases and error handling

### 5. Verify Coverage Restoration
```bash
pytest tests/ --cov=src/sbom_fetcher
```

Confirm coverage is back to 97%+ before committing.

## ✅ Acceptable Exceptions

The following types of code may remain uncovered (27 lines total, 2.65% of codebase):

1. **Entry Points** (2 lines)
   - `__main__.py` - Application entry point
   - Tested via integration tests

2. **Complex Retry Scenarios** (14 lines)
   - `github_client.py` lines 191-193, 210-222
   - Exhausted retry logic with multiple failures
   - Hard to mock reliably in unit tests

3. **Unreachable Defensive Code** (3 lines)
   - `mappers.py` line 78, 110, 199
   - Else statements after return (defensive programming)
   - Unreachable by design

4. **Debug Logging** (3 lines)
   - `parsers.py` lines 148-150
   - ValueError exception logging (rare edge case)

5. **Conditional Progress Logging** (5 lines)
   - `sbom_service.py` lines 153, 163, 232, 261, 281
   - Progress logs triggered every 10-20 items
   - Covered in integration tests

These exceptions are documented and acceptable as they represent:
- Entry points tested differently
- Complex scenarios hard to unit test
- Non-critical code paths (logging/debug)
- Defensive programming practices

## 🎯 New Feature Requirements

When adding new features, ensure:

### Minimum Requirements
- ✅ **95%+ coverage** for all new code
- ✅ **Unit tests** for all public methods
- ✅ **Integration tests** for complete workflows
- ✅ **Edge case tests** (boundaries, errors)
- ✅ **Both success and failure paths** tested

### Test Structure
```python
class TestNewFeature:
    """Tests for new feature."""
    
    @pytest.fixture
    def setup(self):
        """Setup test fixtures."""
        # Setup code
        
    def test_feature_success_path(self, setup):
        """Test successful execution of feature."""
        # Test implementation
        
    def test_feature_with_invalid_input(self, setup):
        """Test feature handles invalid input correctly."""
        # Test implementation
        
    def test_feature_edge_case(self, setup):
        """Test feature handles edge case."""
        # Test implementation
```

### Documentation
- Add docstrings to all test methods
- Explain what is being tested and why
- Document any complex mocking or setup

## 🐛 Bug Fix Requirements

When fixing bugs, follow this workflow:

### 1. Write Failing Test First
```python
def test_bug_reproduction(self):
    """Test that reproduces bug #123."""
    # Arrange: Set up conditions that cause bug
    # Act: Execute code that triggers bug
    # Assert: Verify bug occurs (test should fail)
```

### 2. Fix the Bug
Implement the fix in production code.

### 3. Verify Test Passes
```bash
pytest tests/unit/path/to/test_file.py::test_bug_reproduction -v
```

### 4. Ensure Coverage Maintained
```bash
pytest tests/ --cov=src/sbom_fetcher
```

Verify coverage is still >= 97%.

### 5. Add Regression Tests
If needed, add additional tests to prevent regression:
```python
def test_bug_123_regression_scenario_1(self):
    """Test related scenario to prevent bug #123 regression."""
    # Test implementation
```

## 📈 Test Quality Standards

### Test Naming
- Use descriptive names explaining what is tested
- Format: `test_<function>_<scenario>_<expected_result>`
- Examples:
  - `test_load_token_with_valid_account`
  - `test_parse_purl_scoped_package_with_at_no_version`
  - `test_npm_url_with_branch_reference`

### Test Structure (AAA Pattern)
```python
def test_example(self):
    """Test description."""
    # Arrange: Set up test data and conditions
    mapper = NPMPackageMapper(Config())
    mock_data = {"repository": {"url": "github:owner/repo"}}
    
    # Act: Execute the code being tested
    result = mapper.map_to_github("test-package")
    
    # Assert: Verify the expected outcome
    assert result is not None
    assert result.owner == "owner"
    assert result.repo == "repo"
```

### Docstrings
All tests must have docstrings explaining:
- What is being tested
- Why it's important
- Any special conditions or edge cases

### Mocking
- Mock external dependencies (network, filesystem)
- Use `unittest.mock` or `pytest-mock`
- Keep mocks simple and focused
- Document complex mock setups

### Assertions
- Use specific assertions (`assert x == 5` not just `assert x`)
- Test one concept per test method
- Include failure messages when helpful:
  ```python
  assert result is not None, "Mapper should return result for valid package"
  ```

## 🔒 CI/CD Pipeline Enforcement

The CI/CD pipeline automatically enforces coverage requirements:

### GitHub Actions Workflow
Located in `.github/workflows/ci.yml`:

```yaml
- name: Run tests with pytest
  run: |
    pytest tests/ -v \
      --cov=sbom_fetcher \
      --cov-report=xml \
      --cov-report=html \
      --cov-report=term-missing \
      --junitxml=junit.xml
```

### Coverage Thresholds
- **Hard Minimum:** 95% (build fails below this)
- **Target:** 97%+ (best practice)
- **Current:** 97.35%

### CI Checks
All PRs must pass:
- ✅ All tests passing (319+)
- ✅ Coverage >= 95%
- ✅ Code quality (black, isort, flake8)
- ✅ Type checking (mypy)
- ✅ Security scans
- ✅ No lint errors

### Coverage Reports
- Generated in `htmlcov/` directory
- XML report for Codecov integration
- Terminal output shows summary
- Failed builds show coverage delta

## 📚 Additional Resources

### Testing Documentation
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

### Project Testing Structure
```
tests/
├── unit/
│   ├── application/
│   │   ├── test_main.py
│   │   └── test_main_account_loading.py
│   ├── domain/
│   │   ├── test_exceptions.py
│   │   └── test_models.py
│   ├── infrastructure/
│   │   ├── test_config.py
│   │   ├── test_filesystem.py
│   │   └── test_http_client.py
│   └── services/
│       ├── test_github_client.py
│       ├── test_mapper_edge_cases.py
│       ├── test_mapper_factory.py
│       ├── test_mappers.py
│       ├── test_parser_edge_cases.py
│       ├── test_parsers.py
│       ├── test_pypi_mapper_improvements.py
│       ├── test_reporters.py
│       ├── test_sbom_service.py
│       └── ...
└── integration/
    └── test_e2e.py
```

### Test Coverage History
- **Initial:** ~92%
- **After Component Count Feature:** 95.42%
- **After PyPI Mapper Improvements:** 95.49%
- **Current (with Edge Case Tests):** 97.35%

## 🎯 Summary

**CRITICAL RULES:**
1. ✅ Maintain **97%+ coverage** at all times
2. ✅ Write tests FIRST (TDD)
3. ✅ All tests must pass before committing
4. ✅ PR coverage must be >= 97%
5. ✅ Test behavior, not implementation
6. ✅ Cover edge cases and error paths
7. ✅ Document complex tests
8. ✅ Run coverage checks locally before pushing

**Quick Check:**
```bash
pytest tests/ --cov=src/sbom_fetcher && echo "✅ Coverage OK" || echo "❌ Coverage FAILED"
```

---

**This requirement applies to ALL code changes, no exceptions.**

For questions or clarification, refer to this document or check the CI/CD pipeline configuration in `.github/workflows/ci.yml`.
