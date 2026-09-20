from app.main import app


def test_palette_endpoint_declares_a_json_string_array_response() -> None:
    palette_route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/images/{image_id}/palette"
    )
    assert palette_route.response_model == list[str]
