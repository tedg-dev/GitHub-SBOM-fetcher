"""
Integration tests for main() function to achieve 80%+ coverage.

These tests simulate the full workflow of the SBOM fetcher.
"""

import os
import sys
import tempfile
import json
from unittest.mock import Mock, patch, MagicMock
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import github_sbom_api_fetcher


class TestMainFunction:
    """Test the main() function with various scenarios."""
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    @patch('github_sbom_api_fetcher.save_root_sbom')
    @patch('github_sbom_api_fetcher.extract_packages_from_sbom')
    @patch('github_sbom_api_fetcher.map_package_to_github')
    @patch('github_sbom_api_fetcher.download_dependency_sbom')
    @patch('github_sbom_api_fetcher.generate_markdown_report')
    def test_main_success_flow(self, mock_report, mock_download, mock_map,
                                mock_extract, mock_save_root, mock_fetch,
                                mock_build_session, mock_load_token,
                                mock_parse_args):
        """Test successful main() execution flow."""
        # Setup mocks
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        
        # Mock root SBOM
        mock_root_sbom = {
            "sbom": {
                "packages": [
                    {
                        "name": "lodash",
                        "versionInfo": "4.17.21",
                        "externalRefs": [
                            {
                                "referenceType": "purl",
                                "referenceLocator": "pkg:npm/lodash@4.17.21"
                            }
                        ]
                    }
                ]
            }
        }
        mock_fetch.return_value = mock_root_sbom
        
        # Mock packages
        pkg = github_sbom_api_fetcher.PackageDependency(
            name="lodash",
            version="4.17.21",
            purl="pkg:npm/lodash@4.17.21",
            ecosystem="npm",
            github_owner="lodash",
            github_repo="lodash"
        )
        mock_extract.return_value = [pkg]
        
        mock_map.return_value = True
        mock_download.return_value = True
        mock_report.return_value = "report.md"
        
        # Execute
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.output_dir = temp_dir
            result = github_sbom_api_fetcher.main()
        
        # Verify
        assert result == 0
        mock_load_token.assert_called_once()
        mock_build_session.assert_called_once()
        mock_fetch.assert_called_once()
        mock_extract.assert_called_once()
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    def test_main_token_load_failure(self, mock_load_token, mock_parse_args):
        """Test main() when token loading fails."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "nonexistent.json"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.side_effect = FileNotFoundError("Keys file not found")
        
        result = github_sbom_api_fetcher.main()
        
        assert result == 1
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    def test_main_root_sbom_fetch_failure(self, mock_fetch, mock_build_session,
                                           mock_load_token, mock_parse_args):
        """Test main() when root SBOM fetch fails."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        mock_fetch.return_value = None  # SBOM fetch failed
        
        result = github_sbom_api_fetcher.main()
        
        assert result == 1
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    @patch('github_sbom_api_fetcher.save_root_sbom')
    @patch('github_sbom_api_fetcher.extract_packages_from_sbom')
    def test_main_with_no_packages(self, mock_extract, mock_save_root,
                                    mock_fetch, mock_build_session,
                                    mock_load_token, mock_parse_args):
        """Test main() when no packages are found in SBOM."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        
        mock_root_sbom = {"sbom": {"packages": []}}
        mock_fetch.return_value = mock_root_sbom
        mock_extract.return_value = []  # No packages
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.output_dir = temp_dir
            result = github_sbom_api_fetcher.main()
        
        assert result == 0
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    @patch('github_sbom_api_fetcher.save_root_sbom')
    @patch('github_sbom_api_fetcher.extract_packages_from_sbom')
    @patch('github_sbom_api_fetcher.map_package_to_github')
    @patch('github_sbom_api_fetcher.download_dependency_sbom')
    @patch('github_sbom_api_fetcher.generate_markdown_report')
    def test_main_with_mixed_failures(self, mock_report, mock_download,
                                       mock_map, mock_extract, mock_save_root,
                                       mock_fetch, mock_build_session,
                                       mock_load_token, mock_parse_args):
        """Test main() with mix of successful and failed downloads."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        
        mock_root_sbom = {"sbom": {"packages": []}}
        mock_fetch.return_value = mock_root_sbom
        
        # Create packages with different scenarios
        pkg1 = github_sbom_api_fetcher.PackageDependency(
            name="lodash", version="4.17.21",
            purl="pkg:npm/lodash@4.17.21", ecosystem="npm",
            github_owner="lodash", github_repo="lodash"
        )
        pkg2 = github_sbom_api_fetcher.PackageDependency(
            name="async", version="3.2.0",
            purl="pkg:npm/async@3.2.0", ecosystem="npm",
            github_owner="caolan", github_repo="async"
        )
        pkg2.error = "Dependency graph not enabled"
        pkg2.error_type = "permanent"
        
        mock_extract.return_value = [pkg1, pkg2]
        mock_map.return_value = True
        
        # First download succeeds, second fails
        mock_download.side_effect = [True, False]
        mock_report.return_value = "report.md"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.output_dir = temp_dir
            result = github_sbom_api_fetcher.main()
        
        assert result == 0
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    def test_main_keyboard_interrupt(self, mock_parse_args):
        """Test main() handles KeyboardInterrupt gracefully."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        with patch('github_sbom_api_fetcher.load_token',
                   side_effect=KeyboardInterrupt()):
            result = github_sbom_api_fetcher.main()
        
        assert result == 1
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    def test_main_unexpected_exception(self, mock_build_session,
                                        mock_load_token, mock_parse_args):
        """Test main() handles unexpected exceptions."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_build_session.side_effect = Exception("Unexpected error")
        
        result = github_sbom_api_fetcher.main()
        
        assert result == 1
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    @patch('github_sbom_api_fetcher.save_root_sbom')
    @patch('github_sbom_api_fetcher.extract_packages_from_sbom')
    @patch('github_sbom_api_fetcher.map_package_to_github')
    def test_main_with_packages_without_github(self, mock_map, mock_extract,
                                                mock_save_root, mock_fetch,
                                                mock_build_session,
                                                mock_load_token,
                                                mock_parse_args):
        """Test main() with packages that don't map to GitHub."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        
        mock_root_sbom = {"sbom": {"packages": []}}
        mock_fetch.return_value = mock_root_sbom
        
        # Package that won't map to GitHub
        pkg = github_sbom_api_fetcher.PackageDependency(
            name="some-package",
            version="1.0.0",
            purl="pkg:npm/some-package@1.0.0",
            ecosystem="npm"
        )
        mock_extract.return_value = [pkg]
        mock_map.return_value = False  # Mapping fails
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.output_dir = temp_dir
            result = github_sbom_api_fetcher.main()
        
        assert result == 0
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    @patch('github_sbom_api_fetcher.save_root_sbom')
    @patch('github_sbom_api_fetcher.extract_packages_from_sbom')
    @patch('github_sbom_api_fetcher.map_package_to_github')
    @patch('github_sbom_api_fetcher.download_dependency_sbom')
    @patch('github_sbom_api_fetcher.generate_markdown_report')
    def test_main_with_duplicate_repos(self, mock_report, mock_download,
                                        mock_map, mock_extract,
                                        mock_save_root, mock_fetch,
                                        mock_build_session, mock_load_token,
                                        mock_parse_args):
        """Test main() with duplicate repository versions (deduplication)."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        
        mock_root_sbom = {"sbom": {"packages": []}}
        mock_fetch.return_value = mock_root_sbom
        
        # Same repo, different versions
        pkg1 = github_sbom_api_fetcher.PackageDependency(
            name="lodash", version="4.17.5",
            purl="pkg:npm/lodash@4.17.5", ecosystem="npm",
            github_owner="lodash", github_repo="lodash"
        )
        pkg2 = github_sbom_api_fetcher.PackageDependency(
            name="lodash", version="4.17.21",
            purl="pkg:npm/lodash@4.17.21", ecosystem="npm",
            github_owner="lodash", github_repo="lodash"
        )
        
        mock_extract.return_value = [pkg1, pkg2]
        mock_map.return_value = True
        mock_download.return_value = True
        mock_report.return_value = "report.md"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.output_dir = temp_dir
            result = github_sbom_api_fetcher.main()
        
        # Should only download once due to deduplication
        assert result == 0
        assert mock_download.call_count == 1


class TestEdgeCasesInMainFlow:
    """Test edge cases in the main flow."""
    
    @patch('github_sbom_api_fetcher.argparse.ArgumentParser.parse_args')
    @patch('github_sbom_api_fetcher.load_token')
    @patch('github_sbom_api_fetcher.build_session')
    @patch('github_sbom_api_fetcher.fetch_root_sbom')
    @patch('github_sbom_api_fetcher.save_root_sbom')
    @patch('github_sbom_api_fetcher.extract_packages_from_sbom')
    @patch('github_sbom_api_fetcher.map_package_to_github')
    @patch('github_sbom_api_fetcher.download_dependency_sbom')
    @patch('github_sbom_api_fetcher.generate_markdown_report')
    def test_rate_limiting_pause(self, mock_report, mock_download, mock_map,
                                  mock_extract, mock_save_root, mock_fetch,
                                  mock_build_session, mock_load_token,
                                  mock_parse_args):
        """Test that rate limiting pauses are applied."""
        mock_args = Mock()
        mock_args.gh_user = "test-user"
        mock_args.gh_repo = "test-repo"
        mock_args.key_file = "keys.json"
        mock_args.output_dir = "test_output"
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_token.return_value = "test_token"
        mock_session = Mock()
        mock_build_session.return_value = mock_session
        
        mock_root_sbom = {"sbom": {"packages": []}}
        mock_fetch.return_value = mock_root_sbom
        
        # Create 15 packages to trigger rate limiting check
        packages = []
        for i in range(15):
            pkg = github_sbom_api_fetcher.PackageDependency(
                name=f"pkg{i}", version="1.0.0",
                purl=f"pkg:npm/pkg{i}@1.0.0", ecosystem="npm",
                github_owner=f"owner{i}", github_repo=f"repo{i}"
            )
            packages.append(pkg)
        
        mock_extract.return_value = packages
        mock_map.return_value = True
        mock_download.return_value = True
        mock_report.return_value = "report.md"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_args.output_dir = temp_dir
            with patch('github_sbom_api_fetcher.time.sleep') as mock_sleep:
                result = github_sbom_api_fetcher.main()
            
            # Verify rate limiting pause was applied
            assert mock_sleep.called
        
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=github_sbom_api_fetcher",
                 "--cov-report=term"])
