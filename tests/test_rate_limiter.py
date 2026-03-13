"""Tests for the rate limiter."""

import pytest
from app.core.rate_limiter import RateLimiter
from fastapi import HTTPException


def test_rate_limiter_allows_first_request():
    """First request should always pass."""
    limiter = RateLimiter(interval_seconds=10)
    limiter.check(user_id=1)  # should not raise


def test_rate_limiter_blocks_rapid_requests():
    """Second request within interval should raise 429."""
    limiter = RateLimiter(interval_seconds=10)
    limiter.check(user_id=1)
    with pytest.raises(HTTPException) as exc_info:
        limiter.check(user_id=1)
    assert exc_info.value.status_code == 429


def test_rate_limiter_different_users():
    """Different users should have independent limits."""
    limiter = RateLimiter(interval_seconds=10)
    limiter.check(user_id=1)
    limiter.check(user_id=2)  # should not raise
