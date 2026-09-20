from pathlib import Path

from app.services.palette import (
    analyse_jpeg,
    calculate_rgb_stats,
    normalize_rgb_totals,
    palette_rgb_totals,
)


def test_rgb_stats_for_red_and_blue_palettes() -> None:
    assert calculate_rgb_stats([["#ff0000"] * 5, ["#0000ff"] * 5]) == [50, 0, 50]


def test_rgb_stats_always_sums_to_one_hundred() -> None:
    result = calculate_rgb_stats([["#ff0080", "#00ff40", "#1111ff", "#fefefe", "#000000"]])
    assert sum(result) == 100


def test_empty_rgb_stats() -> None:
    assert calculate_rgb_stats([]) == [0, 0, 0]


def test_palette_contribution_and_normalisation() -> None:
    assert palette_rgb_totals(["#ff0000", "#0000ff"]) == (255, 0, 255)
    assert normalize_rgb_totals((255, 0, 255)) == [50, 0, 50]


def test_supplied_jpeg_produces_exactly_five_hex_colours() -> None:
    _, _, colors = analyse_jpeg(Path("tests/fixtures/mr_robot.jpg").read_bytes())
    assert len(colors) == 5
    assert all(color.startswith("#") and len(color) == 7 for color in colors)
