"""Comprehensive unit tests for HTTP client - Complete Coverage."""

from unittest.mock import Mock, patch

import pytest
import requests

from sbom_fetcher.domain.exceptions import APIError
from sbom_fetcher.infrastructure.http_client import (
    MockHTTPClient,
    MockResponse,
    RequestsHTTPClient,
)


class TestRequestsHTTPClient:
    """Tests for RequestsHTTPClient."""

    def test_initialization_with_session(self):
        """Test initialization with provided session."""
        mock_session = Mock(spec=requests.Session)
        client = RequestsHTTPClient(session=mock_session)

        assert client._session == mock_session

    def test_initialization_without_session(self):
        """Test initialization creates default session."""
        client = RequestsHTTPClient()

        assert isinstance(client._session, requests.Session)

    @patch("requests.Session")
    def test_get_success(self, mock_session_class):
        """Test successful GET request."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_session.get.return_value = mock_response

        client = RequestsHTTPClient(session=mock_session)
        response = client.get("https://api.example.com/data")

        assert response.status_code == 200
        assert response.json() == {"data": "test"}
        mock_session.get.assert_called_once_with(
            "https://api.example.com/data",
            timeout=30,
            headers={},
        )

    @patch("requests.Session")
    def test_get_with_timeout(self, mock_session_class):
        """Test GET request with custom timeout."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        client = RequestsHTTPClient(session=mock_session)
        client.get("https://api.example.com/data", timeout=60)

        mock_session.get.assert_called_once_with(
            "https://api.example.com/data", timeout=60, headers={}
        )

    @patch("requests.Session")
    def test_get_with_headers(self, mock_session_class):
        """Test GET request with custom headers."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 200
        mock_session.get.return_value = mock_response

        client = RequestsHTTPClient(session=mock_session)
        headers = {"Authorization": "Bearer token"}
        client.get("https://api.example.com/data", headers=headers)

        mock_session.get.assert_called_once_with(
            "https://api.example.com/data", timeout=30, headers=headers
        )

    @patch("requests.Session")
    def test_get_timeout_error(self, mock_session_class):
        """Test GET request handles timeout error."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.Timeout("Request timed out")

        client = RequestsHTTPClient(session=mock_session)

        with pytest.raises(APIError, match="Request timeout"):
            client.get("https://api.example.com/data")

    @patch("requests.Session")
    def test_get_connection_error(self, mock_session_class):
        """Test GET request handles connection error."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.ConnectionError("Connection failed")

        client = RequestsHTTPClient(session=mock_session)

        with pytest.raises(APIError, match="Connection error"):
            client.get("https://api.example.com/data")

    @patch("requests.Session")
    def test_get_request_exception(self, mock_session_class):
        """Test GET request handles general request exception."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.get.side_effect = requests.RequestException("Request failed")

        client = RequestsHTTPClient(session=mock_session)

        with pytest.raises(APIError, match="HTTP request failed"):
            client.get("https://api.example.com/data")


class TestMockResponse:
    """Tests for MockResponse."""

    def test_mock_response_initialization(self):
        """Test MockResponse initialization."""
        response = MockResponse(status_code=200, json_data={"key": "value"})

        assert response.status_code == 200
        assert response._json_data == {"key": "value"}

    def test_mock_response_default_json_data(self):
        """Test MockResponse with default json data."""
        response = MockResponse(status_code=200)

        assert response._json_data == {}

    def test_mock_response_json(self):
        """Test MockResponse json method."""
        data = {"result": "success"}
        response = MockResponse(status_code=200, json_data=data)

        assert response.json() == data

    def test_mock_response_raise_for_status_success(self):
        """Test raise_for_status for successful response."""
        response = MockResponse(status_code=200)
        response.raise_for_status()  # Should not raise

    def test_mock_response_raise_for_status_error(self):
        """Test raise_for_status for error response."""
        response = MockResponse(status_code=404)

        with pytest.raises(requests.HTTPError, match="HTTP 404"):
            response.raise_for_status()

    def test_mock_response_raise_for_status_server_error(self):
        """Test raise_for_status for server error."""
        response = MockResponse(status_code=500)

        with pytest.raises(requests.HTTPError, match="HTTP 500"):
            response.raise_for_status()


class TestMockHTTPClient:
    """Tests for MockHTTPClient."""

    def test_mock_client_initialization(self):
        """Test MockHTTPClient initialization."""
        client = MockHTTPClient()

        assert isinstance(client._responses, dict)
        assert len(client._responses) == 0

    def test_mock_client_add_response(self):
        """Test adding response to mock client."""
        client = MockHTTPClient()
        response = MockResponse(status_code=200, json_data={"test": "data"})

        client.add_response("https://api.example.com/test", response)

        assert "https://api.example.com/test" in client._responses
        assert client._responses["https://api.example.com/test"] == response

    def test_mock_client_get_success(self):
        """Test getting configured mock response."""
        client = MockHTTPClient()
        response = MockResponse(status_code=200, json_data={"test": "data"})
        client.add_response("https://api.example.com/test", response)

        result = client.get("https://api.example.com/test")

        assert result == response
        assert result.status_code == 200
        assert result.json() == {"test": "data"}

    def test_mock_client_get_not_configured(self):
        """Test getting unconfigured URL raises error."""
        client = MockHTTPClient()

        with pytest.raises(APIError, match="No mock response configured"):
            client.get("https://api.example.com/unconfigured")

    def test_mock_client_get_with_params(self):
        """Test getting response with additional parameters."""
        client = MockHTTPClient()
        response = MockResponse(status_code=200)
        client.add_response("https://api.example.com/test", response)

        # Should work with timeout and headers (they're just ignored)
        result = client.get(
            "https://api.example.com/test",
            timeout=30,
            headers={"Auth": "token"},
        )

        assert result == response

    def test_mock_client_multiple_responses(self):
        """Test mock client with multiple configured responses."""
        client = MockHTTPClient()

        response1 = MockResponse(status_code=200, json_data={"id": 1})
        response2 = MockResponse(status_code=201, json_data={"id": 2})

        client.add_response("https://api.example.com/endpoint1", response1)
        client.add_response("https://api.example.com/endpoint2", response2)

        result1 = client.get("https://api.example.com/endpoint1")
        result2 = client.get("https://api.example.com/endpoint2")

        assert result1.json() == {"id": 1}
        assert result2.json() == {"id": 2}
