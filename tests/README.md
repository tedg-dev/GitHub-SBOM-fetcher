# SBOM Fetcher v2.0 - Test Suite

Comprehensive PyTest-based test suite for the modular v2.0 codebase.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and test configuration
├── unit/                          # Unit tests (isolated component testing)
│   ├── domain/                    # Domain layer tests
│   │   ├── test_models.py         # Data models (PackageDependency, FetcherStats, etc.)
│   │   └── test_exceptions.py     # Custom exceptions
│   ├── infrastructure/            # Infrastructure layer tests
│   │   └── test_config.py         # Configuration management
│   ├── services/                  # Services layer tests
│   │   └── test_parsers.py        # SBOM and PURL parsers
│   └── application/               # Application layer tests
└── integration/                   # Integration tests (component interaction)
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ -v --cov=sbom_fetcher --cov-report=term-missing
```

### Run Specific Test File
```bash
pytest tests/unit/domain/test_models.py -v
```

### Run Specific Test Class
```bash
pytest tests/unit/domain/test_models.py::TestPackageDependency -v
```

### Run Specific Test
```bash
pytest tests/unit/domain/test_models.py::TestPackageDependency::test_create_package_dependency -v
```

### Using setup_environment.sh
```bash
./setup_environment.sh --test
```

## Current Test Coverage

### ✅ Completed (30 passing tests)

**Domain Layer (100% priority components):**
- ✅ `PackageDependency` model - All fields and validation
- ✅ `GitHubRepository` model - Immutability, equality, hashing
- ✅ `FetcherStats` model - Statistics tracking and computed properties
- ✅ `FailureInfo` model - Failure tracking and dict conversion
- ✅ `FetcherResult` model - Result aggregation and success property
- ✅ `ErrorType` enum - All error type constants
- ✅ Custom exceptions - All exception types and inheritance

**Services Layer (Parser components):**
- ✅ `PURLParser` - npm, PyPI, Maven, scoped packages, invalid PURLs
- ✅ `SBOMParser` - Package extraction, filtering, empty/missing handling

**Infrastructure Layer (Partial):**
- ⚠️ `Config` - Basic tests (needs attribute name fixes)

### 🚧 In Progress (To reach >90% coverage)

**High Priority:**
- `github_client.py` (115 lines, 0% coverage)
  - Root SBOM fetching
  - Dependency SBOM downloading
  - HTTP 5xx retry logic
  - Default branch detection
  - Rate limiting handling

- `sbom_service.py` (167 lines, 0% coverage)
  - Main orchestration flow
  - Statistics collection
  - Error handling
  - Report generation

- `reporters.py` (120 lines, 0% coverage)
  - Markdown report generation
  - Failure categorization
  - Version deduplication reporting

- `mappers.py` (90 lines, 0% coverage)
  - NPM package mapping
  - PyPI package mapping
  - GitHub URL extraction

**Medium Priority:**
- `mapper_factory.py` (22 lines)
- `filesystem.py` (63 lines, 30% coverage)
- `http_client.py` (36 lines, 44% coverage)
- `cli.py` (21 lines)
- `main.py` (63 lines)

## Test Fixtures

Shared fixtures are available in `conftest.py`:

- `sample_sbom_data` - Sample SBOM with npm and PyPI packages
- `npm_registry_response_with_repo` - NPM registry response with GitHub repo
- `npm_registry_response_without_repo` - NPM registry response without repo
- `pypi_registry_response_with_repo` - PyPI registry response with GitHub repo
- `pypi_registry_response_without_repo` - PyPI registry response without repo
- `github_sbom_response` - Sample GitHub SBOM API response
- `mock_http_client` - Mock HTTP client for testing
- `mock_github_client` - Mock GitHub client
- `mock_config` - Mock configuration
- `temp_output_dir` - Temporary directory for testing
- `sample_package_dependency` - Sample package dependency object
- `mock_filesystem_repo` - Mock filesystem repository
- `sample_failed_download` - Sample failed download object

## Writing Tests

### Unit Test Example

```python
from sbom_fetcher.domain.models import PackageDependency, ErrorType

class TestPackageDependency:
    """Tests for PackageDependency model."""

    def test_create_package_dependency(self):
        """Test creating a package dependency."""
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21"
        )
        
        assert pkg.name == "lodash"
        assert pkg.version == "4.17.21"
        assert pkg.ecosystem == "npm"
```

### Using Fixtures

```python
def test_extract_packages(self, sample_sbom_data):
    """Test using a fixture."""
    parser = SBOMParser()
    packages = parser.extract_packages(sample_sbom_data, "owner", "repo")
    assert len(packages) > 0
```

### Mocking Example

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test with mocked dependency."""
    mock_client = Mock()
    mock_client.fetch_root_sbom.return_value = {"sbom": {"packages": []}}
    
    # Test code using mock_client
    assert mock_client.fetch_root_sbom.called
```

## Coverage Goals

- **Target:** >90% overall coverage
- **Current:** ~24% overall coverage
- **Priority:** Core business logic (services and domain layers)

## Adding New Tests

1. Create test file in appropriate directory:
   - Unit tests: `tests/unit/<layer>/test_<module>.py`
   - Integration tests: `tests/integration/test_<feature>.py`

2. Use descriptive test names:
   - Format: `test_<what_it_tests>`
   - Example: `test_parse_npm_package_with_scoped_name`

3. Follow AAA pattern:
   - **Arrange:** Set up test data
   - **Act:** Execute the code being tested
   - **Assert:** Verify the results

4. Add docstrings to test methods explaining what they test

5. Use fixtures from `conftest.py` when possible

## Continuous Integration

Tests are configured to run with coverage requirements:
- Minimum coverage: 90%
- Coverage reports: Terminal + HTML (htmlcov/)
- Fails if coverage drops below threshold

## Next Steps

To reach >90% coverage, add tests for:

1. **github_client.py** - Critical for SBOM fetching
   - Mock HTTP responses for different scenarios
   - Test retry logic for 5xx errors
   - Test rate limiting
   - Test default branch detection

2. **sbom_service.py** - Main orchestration
   - Integration tests for complete flow
   - Mock all dependencies
   - Test error handling

3. **reporters.py** - Report generation
   - Test markdown formatting
   - Test statistics calculation
   - Test failure categorization

4. **mappers.py** - Package mapping
   - Mock registry responses
   - Test URL parsing
   - Test different repository URL formats

## Resources

- **pytest Documentation:** https://docs.pytest.org/
- **pytest-cov Documentation:** https://pytest-cov.readthedocs.io/
- **unittest.mock Documentation:** https://docs.python.org/3/library/unittest.mock.html
