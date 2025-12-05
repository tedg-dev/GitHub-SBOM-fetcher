"""Command-line interface."""

import argparse
import logging
from datetime import datetime
from pathlib import Path


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

    Logs to console and automatically saves to docs/logs/ directory.

    Args:
        debug: Enable debug logging
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Create logs directory if it doesn't exist
    log_dir = Path("docs/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamped log filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    log_file = log_dir / f"run_{timestamp}.log"

    # Setup logging to both console and file
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(log_file, encoding="utf-8"),  # File output
        ],
    )

    # Log the file location (only to console, not to log file)
    console_logger = logging.getLogger(__name__)
    console_logger.info(f"Log file: {log_file}")
