"""HTTP client abstraction using Adapter pattern."""

import logging
from typing import Any, Dict, Optional, Protocol

import requests

from ..domain.exceptions import APIError

logger = logging.getLogger(__name__)


class Response(Protocol):
    """HTTP response interface."""

    status_code: int

    def json(self) -> Any:
        """Parse response as JSON."""
        ...

    def raise_for_status(self) -> None:
        """Raise exception for HTTP errors."""
        ...


class HTTPClient(Protocol):
    """HTTP client interface."""

    def get(
        self,
        url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Execute GET request."""
        ...


class RequestsHTTPClient:
    """Production HTTP client using requests library (Adapter pattern)."""

    def __init__(self, session: Optional[requests.Session] = None):
        """Initialize with optional session."""
        self._session = session or requests.Session()

    def get(
        self,
        url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Execute GET request with error handling."""
        try:
            resp = self._session.get(url, timeout=timeout, headers=headers or {}, **kwargs)
            return resp  # requests.Response already matches our Response protocol
        except requests.Timeout as e:
            raise APIError(f"Request timeout: {e}") from e
        except requests.ConnectionError as e:
            raise APIError(f"Connection error: {e}") from e
        except requests.RequestException as e:
            raise APIError(f"HTTP request failed: {e}") from e


class MockResponse:
    """Mock response for testing."""

    def __init__(self, status_code: int, json_data: Optional[Any] = None):
        """Initialize mock response."""
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self) -> Any:
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Mock raise for status."""
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class MockHTTPClient:
    """Mock HTTP client for testing."""

    def __init__(self) -> None:
        """Initialize mock client."""
        self._responses: Dict[str, MockResponse] = {}

    def add_response(self, url: str, response: MockResponse) -> None:
        """Add a mock response for a URL."""
        self._responses[url] = response

    def get(
        self,
        url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> Response:
        """Get mock response."""
        if url not in self._responses:
            raise APIError(f"No mock response configured for {url}", status_code=404)
        return self._responses[url]
