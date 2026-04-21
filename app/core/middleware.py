import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id, path=request.url.path)

        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_error")
            raise
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "request_complete",
            method=request.method,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
        )
        response.headers["X-Request-Id"] = req_id
        return response
