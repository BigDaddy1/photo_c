from typing import Any, ClassVar

from fastapi.responses import Response
from starlette import status


class APIView:
    """Base for declarative, class-based FastAPI endpoints.

    Subclasses declare `url`, `methods`, and optional FastAPI `kwargs`, like the
    API views in driver-performance.  Unimplemented methods have a predictable
    405 response when called directly.
    """

    url: ClassVar[str]
    methods: ClassVar[tuple[str, ...]] = ()
    kwargs: ClassVar[dict[str, Any]] = {}
    method_kwargs: ClassVar[dict[str, dict[str, Any]]] = {}

    def route_kwargs(self, method: str) -> dict[str, Any]:
        return {**self.kwargs, **self.method_kwargs.get(method, {})}

    async def get(self, *args: Any, **kwargs: Any) -> Response:
        return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    async def post(self, *args: Any, **kwargs: Any) -> Response:
        return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    async def put(self, *args: Any, **kwargs: Any) -> Response:
        return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)

    async def delete(self, *args: Any, **kwargs: Any) -> Response:
        return Response(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
