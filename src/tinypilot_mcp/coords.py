from __future__ import annotations


def pixel_to_relative(pixel_x: int, pixel_y: int, width: int, height: int) -> tuple[float, float]:
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid stream resolution: {width}x{height}")
    rel_x = max(0.0, min(1.0, pixel_x / width))
    rel_y = max(0.0, min(1.0, pixel_y / height))
    return rel_x, rel_y


def relative_to_pixel(relative_x: float, relative_y: float, width: int, height: int) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid stream resolution: {width}x{height}")
    pixel_x = int(round(max(0.0, min(1.0, relative_x)) * width))
    pixel_y = int(round(max(0.0, min(1.0, relative_y)) * height))
    return pixel_x, pixel_y


def format_coord_summary(
    relative_x: float,
    relative_y: float,
    width: int | None,
    height: int | None,
) -> str:
    rel = f"relative=({relative_x:.4f}, {relative_y:.4f})"
    if width is None or height is None:
        return rel
    pixel_x, pixel_y = relative_to_pixel(relative_x, relative_y, width, height)
    return f"{rel} pixel=({pixel_x}, {pixel_y}) resolution={width}x{height}"
