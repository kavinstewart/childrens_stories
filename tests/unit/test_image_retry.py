"""Unit tests for image generation retry logic."""

import pytest
from google.genai.errors import ServerError, ClientError


def _make_server_error(code: int = 503, message: str = "Model overloaded") -> ServerError:
    """Create a ServerError for testing."""
    return ServerError(
        code=code,
        response_json={"error": {"code": code, "message": message, "status": "UNAVAILABLE"}},
    )


def _make_client_error(code: int, message: str = "Error") -> ClientError:
    """Create a ClientError for testing."""
    return ClientError(
        code=code,
        response_json={"error": {"code": code, "message": message}},
    )


class TestImageRetryDecorator:
    """Tests for the @image_retry decorator behavior."""

    def test_retries_on_server_error(self):
        """Should retry when ServerError (503) is raised."""
        from backend.config.image import image_retry

        call_count = 0

        @image_retry
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _make_server_error(503, "Model overloaded")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 3  # Failed twice, succeeded on third

    def test_retries_on_client_error_429(self):
        """Should retry when ClientError with 429 status (rate limit) is raised."""
        from backend.config.image import image_retry

        call_count = 0

        @image_retry
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise _make_client_error(429, "Rate limit exceeded")
            return "success"

        result = rate_limited_function()
        assert result == "success"
        assert call_count == 2

    def test_does_not_retry_on_client_error_400(self):
        """Should NOT retry when ClientError with 400 status (bad request) is raised."""
        from backend.config.image import image_retry

        call_count = 0

        @image_retry
        def bad_request_function():
            nonlocal call_count
            call_count += 1
            raise _make_client_error(400, "Bad request")

        with pytest.raises(ClientError):
            bad_request_function()
        assert call_count == 1  # No retry

    def test_does_not_retry_on_client_error_401(self):
        """Should NOT retry when ClientError with 401 status (auth error) is raised."""
        from backend.config.image import image_retry

        call_count = 0

        @image_retry
        def auth_error_function():
            nonlocal call_count
            call_count += 1
            raise _make_client_error(401, "Invalid API key")

        with pytest.raises(ClientError):
            auth_error_function()
        assert call_count == 1  # No retry

    def test_still_retries_on_network_errors(self):
        """Should still retry on network errors (existing behavior)."""
        from backend.config.image import image_retry

        call_count = 0

        @image_retry
        def network_error_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network unreachable")
            return "success"

        result = network_error_function()
        assert result == "success"
        assert call_count == 2

    def test_gives_up_after_max_attempts(self):
        """Should give up after max retry attempts."""
        from backend.config.image import image_retry

        call_count = 0

        @image_retry
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise _make_server_error(503, "Always fails")

        with pytest.raises(ServerError):
            always_fails()
        assert call_count == 3  # Initial + 2 retries = 3 attempts


class TestRetryableExceptions:
    """Tests for RETRYABLE_EXCEPTIONS configuration."""

    def test_includes_server_error(self):
        """RETRYABLE_EXCEPTIONS should include ServerError."""
        from backend.config.image import RETRYABLE_EXCEPTIONS
        from google.genai.errors import ServerError

        assert ServerError in RETRYABLE_EXCEPTIONS

    def test_includes_network_errors(self):
        """RETRYABLE_EXCEPTIONS should include network error types."""
        from backend.config.image import RETRYABLE_EXCEPTIONS

        assert ConnectionError in RETRYABLE_EXCEPTIONS
        assert TimeoutError in RETRYABLE_EXCEPTIONS
        assert BrokenPipeError in RETRYABLE_EXCEPTIONS
        assert OSError in RETRYABLE_EXCEPTIONS
