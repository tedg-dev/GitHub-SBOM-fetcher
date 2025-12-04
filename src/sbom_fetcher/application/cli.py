"""Command-line interface."""

import argparse
import logging


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Preserves exact CLI interface from original script.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="API-based GitHub SBOM dependency fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch dependencies for a repository
  python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot
  
  # With debug logging
  python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --debug
  
  # Custom output directory
  python -m sbom_fetcher --gh-user tedg-dev --gh-repo beatBot --output-dir ./my_sboms
        """,
    )

    parser.add_argument("--gh-user", required=True, help="GitHub repository owner")
    parser.add_argument("--gh-repo", required=True, help="GitHub repository name")
    parser.add_argument("--key-file", default="keys.json", help="Path to keys.json file")
    parser.add_argument("--output-dir", default="sboms", help="Base output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    return parser.parse_args()


def setup_logging(debug: bool = False) -> None:
    """
    Setup logging configuration.

    Preserves exact logging format from original script.

    Args:
        debug: Enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
