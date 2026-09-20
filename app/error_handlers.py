import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("photocolor")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected server errors without exposing internal details to clients."""
    logger.exception(
        "Unhandled request error: method=%s path=%s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
