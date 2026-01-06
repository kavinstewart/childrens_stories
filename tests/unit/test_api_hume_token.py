"""Tests for Hume EVI token endpoint."""

import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tests.unit.conftest import TEST_TOKEN


def create_mock_async_client(mock_response):
    """Create a mock AsyncClient that returns the given response."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestHumeTokenEndpoint:
    """Tests for GET /auth/hume-token endpoint."""

    def test_hume_token_requires_authentication(self, client):
        """Endpoint should require authentication."""
        response = client.get("/auth/hume-token")
        assert response.status_code == 401

    def test_hume_token_success(self, client_with_mocks):
        """Should return Hume access token for authenticated user."""
        client, *_ = client_with_mocks

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "hume-test-token-123"}

        mock_client = create_mock_async_client(mock_response)

        with patch("backend.api.auth.routes.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.api.auth.routes.HUME_API_KEY", "test-api-key"):
                with patch("backend.api.auth.routes.HUME_SECRET_KEY", "test-secret-key"):
                    response = client.get("/auth/hume-token")

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] == "hume-test-token-123"
        assert data["expires_in"] == 1800  # 30 minutes

    def test_hume_token_missing_api_key(self, client_with_mocks):
        """Should return 503 if Hume API key not configured."""
        client, *_ = client_with_mocks

        with patch("backend.api.auth.routes.HUME_API_KEY", ""):
            response = client.get("/auth/hume-token")

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    def test_hume_token_missing_secret_key(self, client_with_mocks):
        """Should return 503 if Hume secret key not configured."""
        client, *_ = client_with_mocks

        with patch("backend.api.auth.routes.HUME_API_KEY", "test-api-key"):
            with patch("backend.api.auth.routes.HUME_SECRET_KEY", ""):
                response = client.get("/auth/hume-token")

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    def test_hume_token_api_error(self, client_with_mocks):
        """Should return 502 if Hume API returns error."""
        client, *_ = client_with_mocks

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = create_mock_async_client(mock_response)

        with patch("backend.api.auth.routes.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.api.auth.routes.HUME_API_KEY", "test-api-key"):
                with patch("backend.api.auth.routes.HUME_SECRET_KEY", "test-secret"):
                    response = client.get("/auth/hume-token")

        assert response.status_code == 502
        assert "hume" in response.json()["detail"].lower()

    def test_hume_token_network_error(self, client_with_mocks):
        """Should return 502 if network error occurs."""
        client, *_ = client_with_mocks

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.api.auth.routes.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.api.auth.routes.HUME_API_KEY", "test-api-key"):
                with patch("backend.api.auth.routes.HUME_SECRET_KEY", "test-secret"):
                    response = client.get("/auth/hume-token")

        assert response.status_code == 502
        assert "connect" in response.json()["detail"].lower()

    def test_hume_token_correct_api_call(self, client_with_mocks):
        """Should call Hume API with correct parameters."""
        client, *_ = client_with_mocks

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token"}

        mock_client = create_mock_async_client(mock_response)

        with patch("backend.api.auth.routes.httpx.AsyncClient", return_value=mock_client):
            with patch("backend.api.auth.routes.HUME_API_KEY", "my-api-key"):
                with patch("backend.api.auth.routes.HUME_SECRET_KEY", "my-secret"):
                    response = client.get("/auth/hume-token")

        # Verify the API was called correctly
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args

        # Check URL
        assert call_args[0][0] == "https://api.hume.ai/oauth2-cc/token"

        # Check auth (Basic auth with api_key:secret_key)
        assert call_args[1]["auth"] == ("my-api-key", "my-secret")

        # Check body
        assert call_args[1]["data"] == {"grant_type": "client_credentials"}
