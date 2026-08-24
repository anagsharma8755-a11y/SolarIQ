import pytest

from backend.geometry.surfaces import extract_surfaces


def test_extract_single_surface():

    building = {
        "building_id": "B001",
        "surfaces": [
            {
                "surface_id": "S001",
                "vertices": [
                    [0, 0, 10],
                    [20, 0, 10],
                    [20, 20, 10],
                    [0, 20, 10],
                ],
            }
        ],
    }

    surfaces = extract_surfaces(building)

    assert len(surfaces) == 1

    surface = surfaces[0]

    assert surface["surface_id"] == "S001"
    assert surface["building_id"] == "B001"

    assert surface["area_m2"] == pytest.approx(
        400.0
    )

    assert surface["tilt_deg"] == pytest.approx(
        0.0
    )

    assert surface["surface_type"] == "roof"


def test_surface_id_generation():

    building = {
        "building_id": "B001",
        "surfaces": [
            {
                "vertices": [
                    [0, 0, 10],
                    [10, 0, 10],
                    [10, 10, 10],
                ]
            }
        ],
    }

    surfaces = extract_surfaces(building)

    assert surfaces[0]["surface_id"] == "B001-S001"


def test_missing_building_id():

    building = {
        "surfaces": []
    }

    with pytest.raises(ValueError):
        extract_surfaces(building)


def test_missing_surfaces():

    building = {
        "building_id": "B001"
    }

    with pytest.raises(ValueError):
        extract_surfaces(building)


def test_invalid_vertices():

    building = {
        "building_id": "B001",
        "surfaces": [
            {
                "surface_id": "S001",
                "vertices": [
                    [0, 0, 0],
                    [1, 1, 1],
                ],
            }
        ],
    }

    with pytest.raises(ValueError):
        extract_surfaces(building)


def test_empty_vertices_list():

    building = {
        "building_id": "B001",
        "surfaces": [
            {
                "surface_id": "S001",
                "vertices": [],
            }
        ],
    }

    with pytest.raises(ValueError, match="does not contain vertices"):
        extract_surfaces(building)


def test_non_numeric_vertices():

    building = {
        "building_id": "B001",
        "surfaces": [
            {
                "surface_id": "S001",
                "vertices": [
                    [0, 0, 0],
                    [10, 0, 0],
                    [10, "abc", 0],
                ],
            }
        ],
    }

    with pytest.raises(ValueError, match="not numeric"):
        extract_surfaces(building)


def test_surfaces_not_a_list():

    building = {
        "building_id": "B001",
        "surfaces": "not_a_list",
    }

    with pytest.raises(ValueError, match="must be a list"):
        extract_surfaces(building)