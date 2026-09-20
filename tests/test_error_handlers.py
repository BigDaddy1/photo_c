import asyncio
import logging

from starlette.requests import Request

from app.error_handlers import unhandled_exception_handler


def test_unhandled_exception_is_logged_and_returns_safe_response(caplog) -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/images",
            "headers": [],
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )

    with caplog.at_level(logging.ERROR, logger="photocolor"):
        try:
            raise RuntimeError("database connection failed")
        except RuntimeError as error:
            response = asyncio.run(unhandled_exception_handler(request, error))

    assert response.status_code == 500
    assert response.body == b'{"detail":"Internal server error"}'
    assert "Unhandled request error: method=GET path=/images" in caplog.text
    assert "database connection failed" in caplog.text
