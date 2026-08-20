import time
import uuid
import logging
from django.conf import settings

logger = logging.getLogger("casaviva.request")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:64]
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        logger.info("request", extra={
            "request_id": request.request_id,
            "user_id": str(request.user.id) if getattr(request, "user", None) and request.user.is_authenticated else None,
            "endpoint": request.path,
            "status": response.status_code,
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
        })
        return response
