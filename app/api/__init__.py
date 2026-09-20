from fastapi import FastAPI

from app.api.base import APIView
from app.api.images import (
    ImageDetailView,
    ImageFileView,
    ImageListView,
    ImagePaletteView,
    ImageUploadView,
)
from app.api.system import HealthView, RgbStatsView


def register_view(app: FastAPI, view_type: type[APIView]) -> None:
    """Register the declared HTTP methods of one class-based API view."""
    view = view_type()
    for method in view.methods:
        endpoint = getattr(view, method)
        app.add_api_route(
            view.url,
            endpoint,
            methods=[method.upper()],
            name=f"{view_type.__name__}.{method}",
            **view.route_kwargs(method),
        )


def setup_routes(app: FastAPI) -> None:
    for view in (
        HealthView,
        ImageUploadView,
        ImageListView,
        ImageDetailView,
        ImagePaletteView,
        ImageFileView,
        RgbStatsView,
    ):
        register_view(app, view)
