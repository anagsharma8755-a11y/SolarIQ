import pytest

from backend.geometry.calculations import (
    calculate_azimuth,
    calculate_normal,
    calculate_polygon_area,
    calculate_tilt,
    classify_surface,
)


def test_calculate_normal_horizontal_surface():
    vertices = [
        [0, 0, 10],
        [20, 0, 10],
        [20, 20, 10],
    ]

    normal = calculate_normal(vertices)

    assert normal == pytest.approx(
        [0.0, 0.0, 1.0]
    )


def test_calculate_normal_vertical_surface():
    vertices = [
        [0, 0, 0],
        [0, 20, 0],
        [0, 20, 10],
    ]

    normal = calculate_normal(vertices)

    assert normal == pytest.approx(
        [1.0, 0.0, 0.0]
    )


def test_calculate_normal_rejects_too_few_vertices():
    vertices = [
        [0, 0, 0],
        [1, 1, 1],
    ]

    with pytest.raises(ValueError):
        calculate_normal(vertices)


def test_calculate_polygon_area_square():
    vertices = [
        [0, 0, 10],
        [20, 0, 10],
        [20, 20, 10],
        [0, 20, 10],
    ]

    area = calculate_polygon_area(vertices)

    assert area == pytest.approx(400.0)


def test_calculate_polygon_area_rectangle():
    vertices = [
        [0, 0, 10],
        [20, 0, 10],
        [20, 10, 10],
        [0, 10, 10],
    ]

    area = calculate_polygon_area(vertices)

    assert area == pytest.approx(200.0)


def test_calculate_polygon_area_rejects_too_few_vertices():
    vertices = [
        [0, 0, 0],
        [1, 1, 1],
    ]

    with pytest.raises(ValueError):
        calculate_polygon_area(vertices)


def test_calculate_tilt_horizontal():
    tilt = calculate_tilt(
        [0.0, 0.0, 1.0]
    )

    assert tilt == pytest.approx(0.0)


def test_calculate_tilt_vertical():
    tilt = calculate_tilt(
        [1.0, 0.0, 0.0]
    )

    assert tilt == pytest.approx(90.0)


def test_calculate_tilt_inverted_horizontal():
    tilt = calculate_tilt(
        [0.0, 0.0, -1.0]
    )

    assert tilt == pytest.approx(0.0)


def test_calculate_azimuth_north():
    azimuth = calculate_azimuth(
        [0.0, 1.0, 0.0]
    )

    assert azimuth == pytest.approx(0.0)


def test_calculate_azimuth_east():
    azimuth = calculate_azimuth(
        [1.0, 0.0, 0.0]
    )

    assert azimuth == pytest.approx(90.0)


def test_calculate_azimuth_south():
    azimuth = calculate_azimuth(
        [0.0, -1.0, 0.0]
    )

    assert azimuth == pytest.approx(180.0)


def test_calculate_azimuth_west():
    azimuth = calculate_azimuth(
        [-1.0, 0.0, 0.0]
    )

    assert azimuth == pytest.approx(270.0)


def test_calculate_azimuth_horizontal_surface():
    azimuth = calculate_azimuth(
        [0.0, 0.0, 1.0]
    )

    assert azimuth == pytest.approx(0.0)


def test_calculate_normal_collinear_vertices():
    vertices = [
        [0, 0, 0],
        [1, 0, 0],
        [2, 0, 0],
    ]

    with pytest.raises(ValueError, match="collinear"):
        calculate_normal(vertices)


def test_calculate_polygon_area_triangle():
    vertices = [
        [0, 0, 0],
        [10, 0, 0],
        [5, 10, 0],
    ]

    area = calculate_polygon_area(vertices)

    assert area == pytest.approx(50.0)


def test_classify_roof():
    surface_type = classify_surface(
        [0.0, 0.0, 1.0]
    )

    assert surface_type == "roof"


def test_classify_ground():
    surface_type = classify_surface(
        [0.0, 0.0, -1.0]
    )

    assert surface_type == "ground"


def test_classify_facade():
    surface_type = classify_surface(
        [1.0, 0.0, 0.0]
    )

    assert surface_type == "facade"


def test_classify_south_facade():
    surface_type = classify_surface(
        [0.0, -1.0, 0.0]
    )

    assert surface_type == "facade"


def test_calculate_tilt_45_degree():
    tilt = calculate_tilt(
        [1.0, 0.0, 1.0]
    )

    assert tilt == pytest.approx(45.0)


def test_classify_boundary_45_degrees_is_facade():
    surface_type = classify_surface(
        [1.0, 0.0, 1.0]
    )

    assert surface_type == "facade"