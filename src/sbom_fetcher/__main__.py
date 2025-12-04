"""Allow package to be run as module: python -m sbom_fetcher"""

import sys

from .application.main import main

if __name__ == "__main__":
    sys.exit(main())
