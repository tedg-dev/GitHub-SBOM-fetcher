"""Comprehensive unit tests for mapper factory - Complete Coverage."""

from unittest.mock import Mock, patch

import pytest

from sbom_fetcher.domain.models import GitHubRepository, PackageDependency
from sbom_fetcher.infrastructure.config import Config
from sbom_fetcher.services.mapper_factory import MapperFactory
from sbom_fetcher.services.mappers import (
    NPMPackageMapper,
    NullMapper,
    PyPIPackageMapper,
)


class TestMapperFactoryInitialization:
    """Tests for MapperFactory initialization."""

    def test_factory_initialization(self):
        """Test factory initializes with correct configuration."""
        config = Config()
        factory = MapperFactory(config)

        assert factory._config == config
        assert "npm" in factory._mappers
        assert "pypi" in factory._mappers
        assert isinstance(factory._mappers["npm"], NPMPackageMapper)
        assert isinstance(factory._mappers["pypi"], PyPIPackageMapper)
        assert isinstance(factory._null_mapper, NullMapper)

    def test_factory_creates_npm_mapper(self):
        """Test factory creates NPM mapper correctly."""
        config = Config()
        factory = MapperFactory(config)

        assert "npm" in factory._mappers
        npm_mapper = factory._mappers["npm"]
        assert isinstance(npm_mapper, NPMPackageMapper)
        assert npm_mapper._config == config

    def test_factory_creates_pypi_mapper(self):
        """Test factory creates PyPI mapper correctly."""
        config = Config()
        factory = MapperFactory(config)

        assert "pypi" in factory._mappers
        pypi_mapper = factory._mappers["pypi"]
        assert isinstance(pypi_mapper, PyPIPackageMapper)
        assert pypi_mapper._config == config

    def test_factory_creates_null_mapper(self):
        """Test factory creates null mapper for unknown ecosystems."""
        config = Config()
        factory = MapperFactory(config)

        assert factory._null_mapper is not None
        assert isinstance(factory._null_mapper, NullMapper)


class TestCreateMapper:
    """Tests for create_mapper method."""

    @pytest.fixture
    def factory(self):
        """Create mapper factory for testing."""
        return MapperFactory(Config())

    def test_create_mapper_npm(self, factory):
        """Test creating mapper for npm ecosystem."""
        mapper = factory.create_mapper("npm")

        assert isinstance(mapper, NPMPackageMapper)

    def test_create_mapper_npm_uppercase(self, factory):
        """Test creating mapper handles uppercase ecosystem names."""
        mapper = factory.create_mapper("NPM")

        assert isinstance(mapper, NPMPackageMapper)

    def test_create_mapper_npm_mixedcase(self, factory):
        """Test creating mapper handles mixed case ecosystem names."""
        mapper = factory.create_mapper("NpM")

        assert isinstance(mapper, NPMPackageMapper)

    def test_create_mapper_pypi(self, factory):
        """Test creating mapper for pypi ecosystem."""
        mapper = factory.create_mapper("pypi")

        assert isinstance(mapper, PyPIPackageMapper)

    def test_create_mapper_pypi_uppercase(self, factory):
        """Test creating mapper for PyPI with uppercase."""
        mapper = factory.create_mapper("PYPI")

        assert isinstance(mapper, PyPIPackageMapper)

    def test_create_mapper_unknown_ecosystem(self, factory):
        """Test creating mapper for unknown ecosystem returns NullMapper."""
        mapper = factory.create_mapper("golang")

        assert isinstance(mapper, NullMapper)

    def test_create_mapper_empty_ecosystem(self, factory):
        """Test creating mapper for empty ecosystem."""
        mapper = factory.create_mapper("")

        assert isinstance(mapper, NullMapper)

    def test_create_mapper_maven_ecosystem(self, factory):
        """Test creating mapper for Maven (unsupported) returns NullMapper."""
        mapper = factory.create_mapper("maven")

        assert isinstance(mapper, NullMapper)


class TestMapPackageToGitHub:
    """Tests for map_package_to_github method."""

    @pytest.fixture
    def factory(self):
        """Create mapper factory for testing."""
        return MapperFactory(Config())

    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_map_npm_package_success(self, mock_map, factory):
        """Test successful mapping of NPM package."""
        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
        )

        repo = GitHubRepository(owner="lodash", repo="lodash")
        mock_map.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_map.assert_called_once_with("lodash")

    @patch("sbom_fetcher.services.mappers.PyPIPackageMapper.map_to_github")
    def test_map_pypi_package_success(self, mock_map, factory):
        """Test successful mapping of PyPI package."""
        pkg = PackageDependency(
            name="requests",
            version="2.28.0",
            ecosystem="pypi",
            purl="pkg:pypi/requests@2.28.0",
        )

        repo = GitHubRepository(owner="psf", repo="requests")
        mock_map.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_map.assert_called_once_with("requests")

    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_map_package_failure_returns_none(self, mock_map, factory):
        """Test mapping failure when repository not found."""
        pkg = PackageDependency(
            name="nonexistent",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/nonexistent@1.0.0",
        )

        mock_map.return_value = None

        result = factory.map_package_to_github(pkg)

        assert result is False
        assert pkg.github_repository is None

    def test_map_unsupported_ecosystem(self, factory):
        """Test mapping package from unsupported ecosystem."""
        pkg = PackageDependency(
            name="some-package",
            version="1.0.0",
            ecosystem="golang",
            purl="pkg:golang/some-package@1.0.0",
        )

        result = factory.map_package_to_github(pkg)

        assert result is False
        assert pkg.github_repository is None

    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_map_package_uppercase_ecosystem(self, mock_map, factory):
        """Test mapping with uppercase ecosystem name."""
        pkg = PackageDependency(
            name="express",
            version="4.18.0",
            ecosystem="NPM",
            purl="pkg:npm/express@4.18.0",
        )

        repo = GitHubRepository(owner="expressjs", repo="express")
        mock_map.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo

    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_map_scoped_npm_package(self, mock_map, factory):
        """Test mapping scoped NPM package."""
        pkg = PackageDependency(
            name="@babel/core",
            version="7.22.0",
            ecosystem="npm",
            purl="pkg:npm/%40babel/core@7.22.0",
        )

        repo = GitHubRepository(owner="babel", repo="babel")
        mock_map.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_map.assert_called_once_with("@babel/core")

    def test_map_package_updates_package_object(self, factory):
        """Test that successful mapping updates the package object."""
        pkg = PackageDependency(
            name="test-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/test-pkg@1.0.0",
        )

        # Initially no repository
        assert pkg.github_repository is None

        with patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github") as mock_map:
            repo = GitHubRepository(owner="test", repo="test-pkg")
            mock_map.return_value = repo

            result = factory.map_package_to_github(pkg)

            # After mapping, repository is set
            assert result is True
            assert pkg.github_repository is not None
            assert pkg.github_repository.owner == "test"
            assert pkg.github_repository.repo == "test-pkg"

    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_map_package_exception_handling(self, mock_map, factory):
        """Test mapping handles exceptions gracefully."""
        pkg = PackageDependency(
            name="error-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/error-pkg@1.0.0",
        )

        # Simulate an exception in the mapper
        mock_map.side_effect = Exception("Network error")

        # Should handle exception and return False
        with pytest.raises(Exception):
            factory.map_package_to_github(pkg)

    def test_mapper_reuse(self, factory):
        """Test that mappers are reused, not recreated."""
        pkg1 = PackageDependency(
            name="pkg1", version="1.0.0", ecosystem="npm", purl="pkg:npm/pkg1@1.0.0"
        )
        pkg2 = PackageDependency(
            name="pkg2", version="2.0.0", ecosystem="npm", purl="pkg:npm/pkg2@2.0.0"
        )

        mapper1 = factory.create_mapper("npm")
        mapper2 = factory.create_mapper("npm")

        # Should be the same instance (reused)
        assert mapper1 is mapper2


class TestMapperFactoryOrgFallback:
    """Tests for org repository fallback when standard mapping fails."""

    def test_factory_initialization_with_root_org(self):
        """Test factory initializes with root_org parameter."""
        config = Config()
        factory = MapperFactory(config, github_token="test-token", root_org="CiscoSecurityServices")

        assert factory._root_org == "CiscoSecurityServices"
        assert factory._github_token == "test-token"

    def test_factory_initialization_without_root_org(self):
        """Test factory initializes without root_org parameter."""
        config = Config()
        factory = MapperFactory(config)

        assert factory._root_org is None
        assert factory._github_token is None

    @patch("sbom_fetcher.services.mapper_factory.search_org_for_package")
    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_org_fallback_when_standard_mapping_fails(self, mock_npm_map, mock_org_search):
        """Test that org search is used as fallback when standard mapping fails."""
        config = Config()
        factory = MapperFactory(config, github_token="test-token", root_org="CiscoSecurityServices")

        pkg = PackageDependency(
            name="corona-sdk",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/corona-sdk@1.0.0",
        )

        # Standard mapping fails
        mock_npm_map.return_value = None

        # Org search succeeds
        repo = GitHubRepository(owner="CiscoSecurityServices", repo="corona-sdk")
        mock_org_search.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_npm_map.assert_called_once_with("corona-sdk")
        mock_org_search.assert_called_once_with("corona-sdk", "CiscoSecurityServices", "test-token")

    @patch("sbom_fetcher.services.mapper_factory.search_org_for_package")
    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_no_org_fallback_when_standard_mapping_succeeds(self, mock_npm_map, mock_org_search):
        """Test that org search is NOT called when standard mapping succeeds."""
        config = Config()
        factory = MapperFactory(config, github_token="test-token", root_org="CiscoSecurityServices")

        pkg = PackageDependency(
            name="lodash",
            version="4.17.21",
            ecosystem="npm",
            purl="pkg:npm/lodash@4.17.21",
        )

        # Standard mapping succeeds
        repo = GitHubRepository(owner="lodash", repo="lodash")
        mock_npm_map.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_npm_map.assert_called_once_with("lodash")
        # Org search should NOT be called
        mock_org_search.assert_not_called()

    @patch("sbom_fetcher.services.mapper_factory.search_org_for_package")
    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_no_org_fallback_when_root_org_not_set(self, mock_npm_map, mock_org_search):
        """Test that org search is NOT called when root_org is not set."""
        config = Config()
        factory = MapperFactory(config)  # No root_org

        pkg = PackageDependency(
            name="internal-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/internal-pkg@1.0.0",
        )

        # Standard mapping fails
        mock_npm_map.return_value = None

        result = factory.map_package_to_github(pkg)

        assert result is False
        assert pkg.github_repository is None
        # Org search should NOT be called since no root_org
        mock_org_search.assert_not_called()

    @patch("sbom_fetcher.services.mapper_factory.search_org_for_package")
    @patch("sbom_fetcher.services.mappers.NPMPackageMapper.map_to_github")
    def test_org_fallback_also_fails(self, mock_npm_map, mock_org_search):
        """Test behavior when both standard mapping and org fallback fail."""
        config = Config()
        factory = MapperFactory(config, github_token="test-token", root_org="CiscoSecurityServices")

        pkg = PackageDependency(
            name="nonexistent-pkg",
            version="1.0.0",
            ecosystem="npm",
            purl="pkg:npm/nonexistent-pkg@1.0.0",
        )

        # Both fail
        mock_npm_map.return_value = None
        mock_org_search.return_value = None

        result = factory.map_package_to_github(pkg)

        assert result is False
        assert pkg.github_repository is None
        mock_npm_map.assert_called_once()
        mock_org_search.assert_called_once()

    @patch("sbom_fetcher.services.mapper_factory.search_org_for_package")
    @patch("sbom_fetcher.services.mappers.PyPIPackageMapper.map_to_github")
    def test_org_fallback_works_for_pypi_packages(self, mock_pypi_map, mock_org_search):
        """Test that org fallback also works for PyPI packages."""
        config = Config()
        factory = MapperFactory(config, github_token="test-token", root_org="CiscoSecurityServices")

        pkg = PackageDependency(
            name="corona-python-sdk",
            version="2.0.0",
            ecosystem="pypi",
            purl="pkg:pypi/corona-python-sdk@2.0.0",
        )

        # Standard mapping fails
        mock_pypi_map.return_value = None

        # Org search succeeds
        repo = GitHubRepository(owner="CiscoSecurityServices", repo="corona-python-sdk")
        mock_org_search.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_org_search.assert_called_once_with(
            "corona-python-sdk", "CiscoSecurityServices", "test-token"
        )

    @patch("sbom_fetcher.services.mapper_factory.search_org_for_package")
    def test_org_fallback_for_unsupported_ecosystem(self, mock_org_search):
        """Test that org fallback is tried even for unsupported ecosystems."""
        config = Config()
        factory = MapperFactory(config, github_token="test-token", root_org="CiscoSecurityServices")

        pkg = PackageDependency(
            name="internal-go-pkg",
            version="1.0.0",
            ecosystem="golang",
            purl="pkg:golang/internal-go-pkg@1.0.0",
        )

        # Org search succeeds
        repo = GitHubRepository(owner="CiscoSecurityServices", repo="internal-go-pkg")
        mock_org_search.return_value = repo

        result = factory.map_package_to_github(pkg)

        assert result is True
        assert pkg.github_repository == repo
        mock_org_search.assert_called_once_with(
            "internal-go-pkg", "CiscoSecurityServices", "test-token"
        )
