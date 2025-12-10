"""
API Key Authentication Module for Legal RAG MCP Server

Provides middleware-based API key authentication for HTTP mode.
Supports multiple API keys, optional key naming, and constant-time validation.

Modes:
- Environment variable mode: Simple, good for 2-10 clients
- Database mode: Scalable, with rate limiting and usage tracking
"""
import logging
import secrets
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class APIKeyConfig:
    """Configuration for API key authentication."""
    enabled: bool
    api_keys: List[str]
    key_names: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> 'APIKeyConfig':
        """Load API key configuration from environment variables.

        Environment variables:
        - MCP_API_AUTH_ENABLED: "true" or "false" (default: "false")
        - MCP_API_KEYS: Comma-separated list of valid API keys
        - MCP_API_KEY_NAMES: Optional comma-separated key:name pairs

        Returns:
            APIKeyConfig: Configured instance
        """
        enabled_str = os.getenv('MCP_API_AUTH_ENABLED', 'false').lower()
        enabled = enabled_str == 'true'

        # Parse API keys
        api_keys_str = os.getenv('MCP_API_KEYS', '')
        api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]

        # Parse optional key names
        key_names = {}
        key_names_str = os.getenv('MCP_API_KEY_NAMES', '')
        if key_names_str:
            for pair in key_names_str.split(','):
                if ':' in pair:
                    key, name = pair.split(':', 1)
                    key_names[key.strip()] = name.strip()

        # Validate configuration
        if enabled and not api_keys:
            logger.warning(
                "MCP_API_AUTH_ENABLED is true but no API keys configured. "
                "Authentication will be DISABLED."
            )
            enabled = False

        return cls(
            enabled=enabled,
            api_keys=api_keys,
            key_names=key_names
        )


def validate_api_key(
    provided_key: str,
    config: APIKeyConfig
) -> Tuple[bool, Optional[str]]:
    """Validate an API key using constant-time comparison.

    Args:
        provided_key: The API key from the request
        config: APIKeyConfig with valid keys

    Returns:
        Tuple of (is_valid, client_name):
        - is_valid: True if key is valid
        - client_name: Name associated with key, or "Unknown" if not named
    """
    for valid_key in config.api_keys:
        if secrets.compare_digest(provided_key, valid_key):
            client_name = config.key_names.get(valid_key, "Unknown")
            return (True, client_name)
    return (False, None)


def create_auth_error_response(
    message: str,
    details: Optional[Dict] = None
) -> JSONResponse:
    """Create a standardized 401 authentication error response.

    Args:
        message: Error message to display
        details: Optional additional error details

    Returns:
        JSONResponse with 401 status code
    """
    error_body = {
        "error": True,
        "error_type": "authentication_error",
        "message": message
    }
    if details:
        error_body["details"] = details

    return JSONResponse(
        status_code=401,
        content=error_body
    )


def create_rate_limit_error_response(
    period: str,
    reset_seconds: int,
    message: Optional[str] = None
) -> JSONResponse:
    """Create a standardized 429 rate limit error response.

    Args:
        period: The period that was exceeded ('minute', 'hour', 'day')
        reset_seconds: Seconds until rate limit resets
        message: Optional custom message

    Returns:
        JSONResponse with 429 status code and rate limit headers
    """
    error_body = {
        "error": True,
        "error_type": "rate_limit_exceeded",
        "message": message or f"Rate limit exceeded for {period}",
        "retry_after": reset_seconds
    }

    return JSONResponse(
        status_code=429,
        content=error_body,
        headers={
            "X-RateLimit-Reset": str(int(time.time() + reset_seconds)),
            "Retry-After": str(reset_seconds)
        }
    )


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API keys from Authorization header.

    Supports two modes:
    - Environment variable mode: Simple validation against config
    - Database mode: Validation with rate limiting and usage tracking
    """

    def __init__(self, app, config: APIKeyConfig, db_client=None):
        """Initialize middleware with API key configuration.

        Args:
            app: ASGI application
            config: APIKeyConfig instance
            db_client: Optional APIKeyDB instance for database mode
        """
        super().__init__(app)
        self.config = config
        self.db_client = db_client
        self.db_mode = db_client is not None

    async def dispatch(self, request: Request, call_next):
        """Process request and validate API key.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler or 401/429 error
        """
        start_time = time.time()

        # Skip authentication for public endpoints
        if request.url.path in ["/health", "/"]:
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            return create_auth_error_response(
                "Missing authentication credentials",
                {
                    "required_header": "Authorization",
                    "format": "Authorization: Bearer <api_key>"
                }
            )

        # Validate Bearer format
        if not auth_header.startswith("Bearer "):
            return create_auth_error_response(
                "Invalid authentication format",
                {
                    "expected_format": "Authorization: Bearer <api_key>",
                    "received_format": auth_header.split()[0] if auth_header else "none"
                }
            )

        # Extract token
        api_key = auth_header.replace("Bearer ", "", 1).strip()

        # Database mode: Full validation with rate limiting
        if self.db_mode and self.db_client:
            # Validate API key from database
            is_valid, key_record = self.db_client.validate_api_key(api_key)

            if not is_valid:
                logger.warning(
                    f"Authentication failed from {request.client.host if request.client else 'unknown'} "
                    f"to {request.url.path}"
                )

                # Log failed request
                await self.db_client.log_api_request(
                    api_key_id="unknown",
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=401,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    error_message="Invalid or expired API key"
                )

                return create_auth_error_response("Invalid or expired API key")

            # Check rate limits
            is_within_limit, exceeded_period, reset_seconds = self.db_client.check_rate_limit(
                key_record["id"],
                key_record
            )

            if not is_within_limit:
                logger.warning(
                    f"Rate limit exceeded ({exceeded_period}) for client '{key_record['client_name']}' "
                    f"from {request.client.host if request.client else 'unknown'}"
                )

                # Log rate limit violation
                await self.db_client.log_api_request(
                    api_key_id=key_record["id"],
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=429,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    error_message=f"Rate limit exceeded: {exceeded_period}"
                )

                return create_rate_limit_error_response(exceeded_period, reset_seconds)

            # Log successful authentication
            client_name = key_record["client_name"]
            logger.info(f"Authenticated request from '{client_name}' to {request.url.path}")

            # Add client info to request state
            request.state.client_name = client_name
            request.state.api_key_id = key_record["id"]

            # Update last_used timestamp (batched)
            self.db_client.update_key_last_used(key_record["id"], increment_requests=True)

            # Process request
            response = await call_next(request)

            # Log request after completion
            response_time_ms = int((time.time() - start_time) * 1000)
            await self.db_client.log_api_request(
                api_key_id=key_record["id"],
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                response_time_ms=response_time_ms
            )

            return response

        # Environment variable mode: Simple validation
        else:
            # Validate API key
            is_valid, client_name = validate_api_key(api_key, self.config)

            if not is_valid:
                logger.warning(
                    f"Authentication failed from {request.client.host if request.client else 'unknown'} "
                    f"to {request.url.path}"
                )
                return create_auth_error_response("Invalid API key")

            # Log successful authentication
            logger.info(
                f"Authenticated request from '{client_name}' to {request.url.path}"
            )

            # Add client name to request state for downstream use
            request.state.client_name = client_name

            # Continue to next handler
            return await call_next(request)


def generate_api_key() -> str:
    """Generate a cryptographically secure random API key.

    Uses 32 bytes of entropy (256 bits) for strong security.

    Returns:
        str: URL-safe base64-encoded random API key
    """
    return secrets.token_urlsafe(32)


if __name__ == "__main__":
    # Generate example API keys for testing
    print("Generated API Keys:\n")
    for i in range(3):
        key = generate_api_key()
        print(f"Key {i+1}: {key}")

    print("\n" + "="*60)
    print("Example Configuration:")
    print("="*60)
    print("\nAdd to .env file:")
    print("MCP_API_AUTH_ENABLED=true")
    print(f"MCP_API_KEYS={generate_api_key()},{generate_api_key()}")
    print("\nOptionally add names:")
    print(f"MCP_API_KEY_NAMES=key1:ClientA,key2:ClientB")
