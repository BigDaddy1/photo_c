from collections import Counter
from io import BytesIO

from PIL import Image, UnidentifiedImageError


class InvalidJpegError(ValueError):
    pass


def analyse_jpeg(content: bytes) -> tuple[int, int, list[str]]:
    """Validate a JPEG and return dimensions plus exactly five dominant colours."""
    try:
        with Image.open(BytesIO(content)) as source:
            if source.format != "JPEG":
                raise InvalidJpegError("Only JPEG images are supported")
            source.load()
            width, height = source.size
            rgb = source.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidJpegError("The uploaded file is not a valid JPEG image") from exc

    rgb.thumbnail((256, 256))
    quantized = rgb.quantize(colors=5, method=Image.Quantize.MEDIANCUT)
    palette_data = quantized.getpalette()
    counts = Counter(quantized.get_flattened_data())

    colors: list[str] = []
    for index, _ in counts.most_common(5):
        red, green, blue = palette_data[index * 3 : index * 3 + 3]
        colors.append(f"#{red:02x}{green:02x}{blue:02x}")

    if not colors:
        raise InvalidJpegError("The uploaded image contains no pixels")
    colors.extend([colors[-1]] * (5 - len(colors)))
    return width, height, colors


def palette_rgb_totals(palette: list[str]) -> tuple[int, int, int]:
    """Return the RGB contribution of one stored palette."""
    totals = [0, 0, 0]
    for color in palette:
        totals[0] += int(color[1:3], 16)
        totals[1] += int(color[3:5], 16)
        totals[2] += int(color[5:7], 16)
    return tuple(totals)


def normalize_rgb_totals(totals: tuple[int, int, int] | list[int]) -> list[int]:
    """Normalise absolute RGB totals to integer percentages summing to 100."""
    totals = list(totals)

    grand_total = sum(totals)
    if grand_total == 0:
        return [0, 0, 0]

    raw = [component * 100 / grand_total for component in totals]
    rounded_down = [int(value) for value in raw]
    remainder = 100 - sum(rounded_down)
    for index in sorted(range(3), key=lambda item: (raw[item] - rounded_down[item], -item), reverse=True)[:remainder]:
        rounded_down[index] += 1
    return rounded_down


def calculate_rgb_stats(palettes: list[list[str]]) -> list[int]:
    """Calculate global RGB statistics from palettes without database aggregates."""
    totals = [0, 0, 0]
    for palette in palettes:
        red, green, blue = palette_rgb_totals(palette)
        totals[0] += red
        totals[1] += green
        totals[2] += blue
    return normalize_rgb_totals(totals)
