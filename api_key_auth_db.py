"""
Database Operations Module for API Key Authentication

Provides database-backed validation, rate limiting, and usage tracking
for API keys stored in Supabase.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, Optional, Tuple
from supabase import Client

logger = logging.getLogger(__name__)


class APIKeyDB:
    """Database operations for API key authentication."""

    def __init__(self, supabase_client: Client):
        """Initialize with Supabase client.

        Args:
            supabase_client: Authenticated Supabase client
        """
        self.client = supabase_client
        self._cache_ttl = 300  # 5 minutes
        self._batch_update_threshold = 10  # Update last_used every 10 requests
        self._request_counts: Dict[str, int] = {}

    def _hash_key(self, api_key: str) -> str:
        """Hash an API key using SHA-256.

        Args:
            api_key: The plaintext API key

        Returns:
            str: Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @lru_cache(maxsize=100)
    def _get_cached_key(self, key_hash: str, cache_key: str) -> Optional[Dict]:
        """Get cached API key record.

        Args:
            key_hash: SHA-256 hash of the API key
            cache_key: Cache invalidation key (timestamp)

        Returns:
            Optional[Dict]: API key record or None
        """
        try:
            result = self.client.table("api_keys").select("*").eq("key_hash", key_hash).eq("is_active", True).execute()

            if not result.data:
                return None

            return result.data[0]

        except Exception as e:
            logger.error(f"Error fetching API key from database: {e}")
            return None

    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[Dict]]:
        """Validate an API key against the database.

        Uses LRU cache with 5-minute TTL for performance.

        Args:
            api_key: The plaintext API key from the request

        Returns:
            Tuple of (is_valid, api_key_record):
            - is_valid: True if key is valid and not expired
            - api_key_record: Full API key record from database
        """
        try:
            key_hash = self._hash_key(api_key)

            # Generate cache key based on current 5-minute window
            cache_window = int(datetime.now().timestamp() / self._cache_ttl)
            cache_key = f"{cache_window}"

            # Get from cache (or database if not cached)
            key_record = self._get_cached_key(key_hash, cache_key)

            if not key_record:
                logger.debug("API key not found or inactive")
                return (False, None)

            # Check expiration
            if key_record.get("expires_at"):
                expires_at = datetime.fromisoformat(key_record["expires_at"].replace("Z", "+00:00"))
                if expires_at < datetime.now():
                    logger.warning(f"API key expired for client '{key_record['client_name']}'")
                    return (False, None)

            logger.debug(f"API key validated successfully for client '{key_record['client_name']}'")
            return (True, key_record)

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return (False, None)

    def check_rate_limit(self, api_key_id: str, key_record: Dict) -> Tuple[bool, Optional[str], Optional[int]]:
        """Check if an API key has exceeded its rate limit.

        Checks minute, hour, and day limits in order.

        Args:
            api_key_id: UUID of the API key
            key_record: API key record containing rate limits

        Returns:
            Tuple of (is_within_limit, period, remaining):
            - is_within_limit: True if within all rate limits
            - period: The period that was exceeded ('minute', 'hour', or 'day'), or None
            - remaining: Seconds until rate limit resets, or None
        """
        try:
            # Get rate limits (use defaults if not specified)
            limit_per_minute = key_record.get("rate_limit_per_minute", 60)
            limit_per_hour = key_record.get("rate_limit_per_hour", 1000)
            limit_per_day = key_record.get("rate_limit_per_day", 10000)

            # Check minute limit
            if limit_per_minute:
                result = self.client.rpc("check_rate_limit", {
                    "p_api_key_id": api_key_id,
                    "p_period": "minute",
                    "p_limit": limit_per_minute
                }).execute()

                if result.data and not result.data[0]["is_within_limit"]:
                    logger.warning(f"Rate limit exceeded (minute) for key {api_key_id}")
                    return (False, "minute", 60)

            # Check hour limit
            if limit_per_hour:
                result = self.client.rpc("check_rate_limit", {
                    "p_api_key_id": api_key_id,
                    "p_period": "hour",
                    "p_limit": limit_per_hour
                }).execute()

                if result.data and not result.data[0]["is_within_limit"]:
                    logger.warning(f"Rate limit exceeded (hour) for key {api_key_id}")
                    return (False, "hour", 3600)

            # Check day limit
            if limit_per_day:
                result = self.client.rpc("check_rate_limit", {
                    "p_api_key_id": api_key_id,
                    "p_period": "day",
                    "p_limit": limit_per_day
                }).execute()

                if result.data and not result.data[0]["is_within_limit"]:
                    logger.warning(f"Rate limit exceeded (day) for key {api_key_id}")
                    return (False, "day", 86400)

            return (True, None, None)

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # On error, allow the request (fail open)
            return (True, None, None)

    async def log_api_request(
        self,
        api_key_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log an API request to the database (fire-and-forget).

        Args:
            api_key_id: UUID of the API key
            endpoint: Request endpoint (e.g., "/mcp/v1/tools/call")
            method: HTTP method (e.g., "POST")
            status_code: HTTP status code
            ip_address: Client IP address
            user_agent: Client User-Agent header
            response_time_ms: Response time in milliseconds
            error_message: Error message if request failed
            metadata: Additional metadata (tool name, parameters, etc.)
        """
        try:
            data = {
                "api_key_id": api_key_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "metadata": metadata or {}
            }

            # Add optional fields if provided
            if response_time_ms is not None:
                data["metadata"]["response_time_ms"] = response_time_ms

            if error_message:
                data["error_message"] = error_message

            # Insert asynchronously (fire-and-forget)
            self.client.table("api_key_usage").insert(data).execute()

            logger.debug(f"Logged API request for key {api_key_id}")

        except Exception as e:
            # Don't fail the request if logging fails
            logger.error(f"Error logging API request: {e}")

    def update_key_last_used(self, api_key_id: str, increment_requests: bool = True):
        """Update the last_used_at timestamp and total_requests for an API key.

        Uses batching to reduce database writes (updates every 10 requests).

        Args:
            api_key_id: UUID of the API key
            increment_requests: Whether to increment total_requests counter
        """
        try:
            # Increment request count
            if increment_requests:
                self._request_counts[api_key_id] = self._request_counts.get(api_key_id, 0) + 1

            # Only update database every N requests
            request_count = self._request_counts.get(api_key_id, 0)
            if request_count % self._batch_update_threshold == 0:
                update_data = {
                    "last_used_at": datetime.now().isoformat()
                }

                if increment_requests:
                    # Increment by the accumulated count
                    update_data["total_requests"] = self.client.table("api_keys").select("total_requests").eq("id", api_key_id).execute().data[0]["total_requests"] + request_count
                    self._request_counts[api_key_id] = 0  # Reset counter

                self.client.table("api_keys").update(update_data).eq("id", api_key_id).execute()

                logger.debug(f"Updated last_used_at for key {api_key_id}")

        except Exception as e:
            # Don't fail the request if update fails
            logger.error(f"Error updating key last_used: {e}")

    def get_key_info(self, api_key_id: str) -> Optional[Dict]:
        """Get full information about an API key.

        Args:
            api_key_id: UUID of the API key

        Returns:
            Optional[Dict]: API key record or None if not found
        """
        try:
            result = self.client.table("api_keys").select("*").eq("id", api_key_id).execute()

            if not result.data:
                return None

            return result.data[0]

        except Exception as e:
            logger.error(f"Error getting key info: {e}")
            return None

    def get_usage_stats(self, api_key_id: str, days: int = 7) -> Optional[list]:
        """Get usage statistics for an API key.

        Args:
            api_key_id: UUID of the API key
            days: Number of days to retrieve

        Returns:
            Optional[list]: List of daily usage statistics
        """
        try:
            result = self.client.rpc("get_api_key_usage_stats", {
                "p_api_key_id": api_key_id,
                "p_days": days
            }).execute()

            return result.data

        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return None

    def clear_cache(self):
        """Clear the API key cache.

        Useful after creating, revoking, or modifying API keys.
        """
        self._get_cached_key.cache_clear()
        logger.info("API key cache cleared")


# Convenience function for getting a database client
def create_api_key_db(supabase_client: Client) -> APIKeyDB:
    """Create an APIKeyDB instance.

    Args:
        supabase_client: Authenticated Supabase client

    Returns:
        APIKeyDB: Database operations client
    """
    return APIKeyDB(supabase_client)
