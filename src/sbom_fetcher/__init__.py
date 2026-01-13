"""SBOM Fetcher - Production-grade GitHub SBOM dependency fetcher."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sbom-fetcher")
except PackageNotFoundError:
    __version__ = "0.0.0"

__author__ = "SBOM Fetcher Team"
__license__ = "MIT"
