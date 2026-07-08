import pytest

from tinypilot_mcp.coords import format_coord_summary, pixel_to_relative, relative_to_pixel


def test_pixel_to_relative_center() -> None:
    rel_x, rel_y = pixel_to_relative(512, 384, 1024, 768)
    assert rel_x == pytest.approx(0.5)
    assert rel_y == pytest.approx(0.5)


def test_relative_to_pixel_roundtrip() -> None:
    rel_x, rel_y = pixel_to_relative(271, 489, 1024, 768)
    pixel_x, pixel_y = relative_to_pixel(rel_x, rel_y, 1024, 768)
    assert pixel_x == 271
    assert pixel_y == 489


def test_format_coord_summary() -> None:
    text = format_coord_summary(0.265, 0.638, 1024, 768)
    assert "relative=(0.2650, 0.6380)" in text
    assert "pixel=(271, 490)" in text
    assert "resolution=1024x768" in text
