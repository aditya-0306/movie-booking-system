"""
Sliding-window rate limiter, same Redis sorted-set approach used in the
URL shortener project — but applied here as global ASGI middleware instead
of a per-route dependency, so every request is covered without having to
remember to add it to each new endpoint.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.utils.redis_client import redis_client


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Health checks and docs shouldn't count against a client's limit
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"rate_limit:{client_ip}"
        now = time.time()
        window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS

        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, settings.RATE_LIMIT_WINDOW_SECONDS)
        _, request_count, _, _ = pipe.execute()

        if request_count >= settings.RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded: max {settings.RATE_LIMIT_REQUESTS} "
                        f"requests per {settings.RATE_LIMIT_WINDOW_SECONDS} seconds."
                    )
                },
            )

        return await call_next(request)
