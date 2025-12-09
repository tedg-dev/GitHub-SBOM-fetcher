"""Main application entry point with dependency injection."""

import json
import logging
import sys
from pathlib import Path

import requests

from ..domain.exceptions import TokenLoadError
from ..infrastructure.config import Config
from ..infrastructure.filesystem import FilesystemSBOMRepository
from ..services.github_client import GitHubClient
from ..services.mapper_factory import MapperFactory
from ..services.reporters import MarkdownReporter
from ..services.sbom_service import SBOMFetcherService

logger = logging.getLogger(__name__)


def load_token(key_file: Path, account: str = None) -> str:
    """
    Load GitHub token from keys file for specified account.

    Args:
        key_file: Path to keys.json file
        account: Account username to look up (e.g., 'tedg-dev', 'tedg-cisco')

    Returns:
        GitHub token string

    Raises:
        TokenLoadError: If token cannot be loaded
    """
    try:
        with open(key_file, "r") as f:
            data = json.load(f)

        # If account specified, search accounts array
        if account:
            accounts = data.get("accounts", [])
            for acc in accounts:
                if acc.get("username") == account:
                    token = acc.get("token")
                    if token:
                        logger.info(f"Using account: {account}")
                        return token
                    else:
                        raise TokenLoadError(f"Account '{account}' found but has no token")

            # Account not found
            available = [acc.get("username") for acc in accounts if acc.get("username")]
            raise TokenLoadError(
                f"Account '{account}' not found in keys file. "
                f"Available accounts: {', '.join(available) if available else 'none'}"
            )

        # Fallback: Try different key formats (backward compatibility)
        token = (
            data.get("github_token")
            or data.get("token")
            or (data.get("accounts", [{}])[0].get("token") if data.get("accounts") else None)
        )

        if not token:
            raise TokenLoadError("No GitHub token found in keys file")

        return token

    except FileNotFoundError:
        raise TokenLoadError(f"Keys file '{key_file}' not found. Create it with your GitHub token.")
    except json.JSONDecodeError:
        raise TokenLoadError(f"Invalid JSON in keys file '{key_file}'")


def build_session(token: str) -> requests.Session:
    """
    Build requests session with GitHub authentication.

    Preserves exact behavior from original build_session function.

    Args:
        token: GitHub API token

    Returns:
        Configured requests.Session
    """
    s = requests.Session()
    s.headers.update(
        {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-sbom-api-fetcher/1.0",
        }
    )
    return s


def create_service(config: Config, token: str) -> SBOMFetcherService:
    """
    Create SBOMFetcherService with all dependencies injected.

    Args:
        config: Application configuration
        token: GitHub API token

    Returns:
        Fully configured SBOMFetcherService
    """
    # Create HTTP client (wrapped in RequestsHTTPClient if needed, but for now
    # we pass session directly to maintain compatibility)
    from ..infrastructure.http_client import RequestsHTTPClient

    http_client = RequestsHTTPClient()

    # Create GitHub client
    github_client = GitHubClient(http_client, token, config)

    # Create mapper factory
    mapper_factory = MapperFactory(config)

    # Create repository
    repository = FilesystemSBOMRepository(config.output_dir)

    # Create reporter
    reporter = MarkdownReporter()

    # Create and return service
    return SBOMFetcherService(
        github_client=github_client,
        mapper_factory=mapper_factory,
        repository=repository,
        reporter=reporter,
        config=config,
    )


def main() -> int:
    """
    Main entry point.

    Preserves exact behavior from original main() function.

    Returns:
        Exit code (0 for success, 1 for error, 130 for KeyboardInterrupt)
    """
    from .cli import parse_arguments, setup_logging

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(args.debug)

    try:
        # Load configuration
        config = Config.load()

        # Override with CLI args
        if args.output_dir:
            config.output_dir = Path(args.output_dir)
        if args.key_file:
            config.key_file = Path(args.key_file)

        # Load token for specified account
        logger.info("Loading GitHub token...")
        token = load_token(config.key_file, args.account)

        # Build session
        session = build_session(token)

        # Create service
        service = create_service(config, token)

        # Run workflow
        result = service.fetch_all_sboms(args.gh_user, args.gh_repo, session)

        # Log final note
        logger.info("✅ Done!")

        return 0

    except KeyboardInterrupt:
        logger.info("\n\n❌ Interrupted by user")
        return 130
    except TokenLoadError as e:
        logger.error("❌ Token error: %s", e)
        return 1
    except Exception as e:
        logger.error("❌ Fatal error: %s", e, exc_info=args.debug if "args" in locals() else False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
