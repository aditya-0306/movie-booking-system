import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            f'{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)'
        )
        return response
