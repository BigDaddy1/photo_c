from typing import ClassVar

from app.api.base import APIView
from app.db.models import COLOR_STATISTICS_ID, ColorStatistics
from app.schemas import HealthResponse
from app.services.palette import normalize_rgb_totals


class HealthView(APIView):
    url: ClassVar[str] = "/health"
    methods: ClassVar[tuple[str, ...]] = ("get",)
    kwargs: ClassVar[dict[str, object]] = {"response_model": HealthResponse}

    async def get(self) -> HealthResponse:
        return HealthResponse(status="ok")


class RgbStatsView(APIView):
    url: ClassVar[str] = "/rgbstats"
    methods: ClassVar[tuple[str, ...]] = ("get",)
    kwargs: ClassVar[dict[str, object]] = {"response_model": list[int]}

    async def get(self) -> list[int]:
        statistics = await ColorStatistics.get(COLOR_STATISTICS_ID)
        if statistics is None:
            return [0, 0, 0]
        return normalize_rgb_totals(
            (statistics.total_red, statistics.total_green, statistics.total_blue)
        )
