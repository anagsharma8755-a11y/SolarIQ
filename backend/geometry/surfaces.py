from __future__ import annotations

from typing import Any

from backend.geometry.calculations import (
    analyze_polygon_batch,
    calculate_azimuth,
    calculate_bounding_box,
    calculate_centroid,
    calculate_normal,
    calculate_polygon_area,
    calculate_tilt,
    classify_surface,
    is_degenerate_polygon,
    is_reversed_winding,
    normalise_winding,
)


def _validate_vertices(
    vertices: Any,
    surface_id: str,
) -> None:
    """
    Validate vertex structure before geometric calculation.

    Raises:
        ValueError: if vertices are malformed.
    """

    if not isinstance(vertices, list):
        raise ValueError(
            f"Surface {surface_id}: vertices must be a list."
        )

    if len(vertices) < 3:
        raise ValueError(
            f"Surface {surface_id}: at least three vertices are required."
        )

    for idx, vertex in enumerate(vertices):
        if not isinstance(vertex, list):
            raise ValueError(
                f"Surface {surface_id}: vertex {idx} must be a list."
            )

        if len(vertex) != 3:
            raise ValueError(
                f"Surface {surface_id}: vertex {idx} must have exactly 3 values."
            )

        for coord_idx, coord in enumerate(vertex):
            if not isinstance(coord, (int, float)):
                raise ValueError(
                    f"Surface {surface_id}: vertex {idx}, "
                    f"coordinate {coord_idx} is not numeric."
                )


def extract_surfaces(building: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract and analyze all surfaces belonging to a building.

    Expected input:

    {
        "building_id": "B001",
        "surfaces": [
            {
                "surface_id": "S001",
                "vertices": [
                    [0, 0, 10],
                    [20, 0, 10],
                    [20, 20, 10],
                    [0, 20, 10]
                ]
            }
        ]
    }

    Output fields include original geometry, computed
    normal, tilt, azimuth, surface_type, plus new metadata:
    centroid, bounding_box, reversed_winding, degenerate.
    """

    building_id = building.get("building_id")

    if not building_id:
        raise ValueError("Building must contain a building_id.")

    raw_surfaces = building.get("surfaces")

    if not isinstance(raw_surfaces, list):
        raise ValueError("Building surfaces must be a list.")

    analyzed_surfaces = []

    for index, surface in enumerate(raw_surfaces, start=1):
        surface_id = surface.get("surface_id") or f"{building_id}-S{index:03d}"

        vertices = surface.get("vertices")

        if not vertices:
            raise ValueError(
                f"Surface {surface_id} does not contain vertices."
            )

        _validate_vertices(vertices, surface_id)

        # Single-pass geometry analysis (replaces 7 separate calls).
        result = analyze_polygon_batch(vertices)

        reversed_winding = result["reversed_winding"]
        if reversed_winding:
            vertices = result["points"]
            vertices = [[float(c) for c in v] for v in vertices]

        analyzed_surfaces.append(
            {
                "surface_id": surface_id,
                "building_id": building_id,
                "area_m2": round(result["area_m2"], 4),
                "normal": {
                    "x": round(result["normal"][0], 6),
                    "y": round(result["normal"][1], 6),
                    "z": round(result["normal"][2], 6),
                },
                "azimuth_deg": round(result["azimuth_deg"], 2),
                "tilt_deg": round(result["tilt_deg"], 2),
                "surface_type": result["surface_type"],
                "vertices": vertices,
                # --- new metadata ---
                "centroid": [round(c, 6) for c in result["centroid"]],
                "bounding_box": {
                    k: round(v, 6) for k, v in result["bounding_box"].items()
                },
                "reversed_winding_corrected": reversed_winding,
            }
        )

    return analyzed_surfaces
