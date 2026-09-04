import time
import uuid
import logging
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings

logger = logging.getLogger("app.access")

# Simple in-memory sliding window rate limiter
class RateLimiter:
    def __init__(self, requests_per_minute: int = 120):
        self.rpm = requests_per_minute
        self.hits: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        if not settings.RATE_LIMITING_ENABLED:
            return True
        now = time.time()
        window_start = now - 60.0
        # Clean expired timestamps
        self.hits[client_ip] = [t for t in self.hits[client_ip] if t > window_start]
        if len(self.hits[client_ip]) >= self.rpm:
            return False
        self.hits[client_ip].append(now)
        return True

rate_limiter = RateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        client_ip = request.client.host if request.client else "unknown"

        # Rate Limiting Check (Exclude Health and Docs)
        path = request.url.path
        if not path.startswith("/api/v1/health") and not path.startswith("/docs") and not path.startswith("/openapi.json"):
            if not rate_limiter.is_allowed(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip} on {path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please slow down.",
                        "request_id": request_id
                    },
                    headers={"X-Request-ID": request_id}
                )

        start_time = time.time()
        response: Response
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(
                f"Request failed: {request.method} {path} | Status: 500 | "
                f"Duration: {duration_ms:.2f}ms | IP: {client_ip} | RequestID: {request_id} | Error: {str(exc)}"
            )
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal error occurred.",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )

        duration_ms = (time.time() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id

        # Log structured request summary (sanitize headers)
        logger.info(
            f"{request.method} {path} | Status: {response.status_code} | "
            f"Duration: {duration_ms:.2f}ms | IP: {client_ip} | RequestID: {request_id}"
        )
        return response
