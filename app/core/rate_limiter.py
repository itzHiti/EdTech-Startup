import time
from fastapi import HTTPException, status


class RateLimiter:
    """In-memory per-user rate limiter for ChatGPT API requests.

    Enforces a minimum interval of `interval_seconds` between requests for each user.
    """

    def __init__(self, interval_seconds: int = 10):
        self.interval = interval_seconds
        self._last_request: dict[int, float] = {}

    def check(self, user_id: int) -> None:
        now = time.time()
        last = self._last_request.get(user_id, 0.0)
        elapsed = now - last
        if elapsed < self.interval:
            wait = self.interval - elapsed
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {wait:.1f} seconds before the next AI request.",
            )
        self._last_request[user_id] = now


# Global instance – imported by routers that call OpenAI
gpt_rate_limiter = RateLimiter(interval_seconds=10)
