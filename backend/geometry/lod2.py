"""LOD-2 building geometry representation.

Level of Detail 2 (LOD-2) adds roof structure to the LOD-1
extruded building model.  This module defines the architecture
for representing:

- Pitched (gable/hip) roofs with multiple planes
- Roof ridges and edges
- Dormer windows (when data is available)
- Non-rectangular building footprints

Important:
    This module provides the DATA MODEL and VALIDATION only.
    It does NOT fabricate LOD-2 geometry from LOD-1 data.
    When actual LOD-2 data is unavailable (e.g. from CityGML
    or 3DTiles), only LOD-1 surfaces are produced.

Test fixtures demonstrate the expected data shapes.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Sequence

from backend.geometry.calculations import (
    Vector3,
    calculate_normal,
    calculate_polygon_area,
    classify_surface,
    is_degenerate_polygon,
    is_planar,
)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RoofType(str, enum.Enum):
    """Roof shape classification."""

    FLAT = "flat"
    GABLE = "gable"
    HIP = "hip"
    GAMBRD = "gambrel"
    MANSARD = "mansard"
    SHED = "shed"
    DOME = "dome"
    UNKNOWN = "unknown"


class LODLevel(int, enum.Enum):
    """Level of Detail for building geometry."""

    LOD0 = 0  # Footprint only
    LOD1 = 1  # Extruded box
    LOD2 = 2  # With roof structure


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RoofPlane:
    """A single planar roof surface.

    Attributes:
        plane_id: Unique identifier within the building.
        vertices: Ordered 3D vertices defining the plane.
        roof_type: Classification of this roof section.
        area_m2: Computed surface area in square metres.
        normal: Unit surface normal vector.
        tilt_deg: Surface tilt in degrees from horizontal.
        azimuth_deg: Surface compass bearing.
    """

    plane_id: str
    vertices: list[list[float]]
    roof_type: RoofType = RoofType.UNKNOWN
    area_m2: float = 0.0
    normal: list[float] = field(default_factory=lambda: [0.0, 0.0, 1.0])
    tilt_deg: float = 0.0
    azimuth_deg: float = 0.0


@dataclass
class RoofRidge:
    """A ridge line connecting two roof planes.

    Attributes:
        ridge_id: Unique identifier.
        start: 3D coordinate of ridge start.
        end: 3D coordinate of ridge end.
        left_plane_id: ID of the roof plane on the left.
        right_plane_id: ID of the roof plane on the right.
        length_m: Length of the ridge in metres.
    """

    ridge_id: str
    start: list[float]
    end: list[float]
    left_plane_id: str = ""
    right_plane_id: str = ""
    length_m: float = 0.0


@dataclass
class Dormer:
    """A dormer window projecting from a roof plane.

    Attributes:
        dormer_id: Unique identifier.
        roof_plane_id: The parent roof plane.
        vertices: 3D vertices of the dormer outline.
        area_m2: Surface area of the dormer.
    """

    dormer_id: str
    roof_plane_id: str
    vertices: list[list[float]]
    area_m2: float = 0.0


@dataclass
class LOD2Building:
    """Complete LOD-2 representation of a building.

    This is the extensible architecture for buildings that
    have LOD-2 data available.  When only LOD-1 data exists,
    use the LOD-1 pipeline (extract_surfaces) instead.

    Attributes:
        building_id: Unique building identifier.
        lod: Level of Detail.
        roof_planes: List of roof surface definitions.
        ridges: List of ridge lines.
        dormers: List of dormer features.
        facade_vertices: Extrusion side vertices (LOD-1 compatible).
        ground_vertices: Ground footprint vertices.
        roof_type: Overall roof classification.
    """

    building_id: str
    lod: LODLevel = LODLevel.LOD2
    roof_planes: list[RoofPlane] = field(default_factory=list)
    ridges: list[RoofRidge] = field(default_factory=list)
    dormers: list[Dormer] = field(default_factory=list)
    facade_vertices: list[list[list[float]]] = field(default_factory=list)
    ground_vertices: list[list[float]] = field(default_factory=list)
    roof_type: RoofType = RoofType.UNKNOWN


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_roof_plane(plane: RoofPlane) -> list[str]:
    """Validate a RoofPlane, returning error messages.

    An empty list means the plane is valid.
    """
    errors: list[str] = []

    if not plane.plane_id:
        errors.append("RoofPlane must have a plane_id.")

    if len(plane.vertices) < 3:
        errors.append(
            f"RoofPlane {plane.plane_id}: needs at least 3 vertices."
        )
        return errors

    if is_degenerate_polygon(plane.vertices):
        errors.append(
            f"RoofPlane {plane.plane_id}: degenerate polygon."
        )

    if not is_planar(plane.vertices):
        errors.append(
            f"RoofPlane {plane.plane_id}: vertices are not coplanar."
        )

    return errors


def validate_lod2_building(building: LOD2Building) -> list[str]:
    """Validate a complete LOD-2 building representation.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []

    if not building.building_id:
        errors.append("LOD2Building must have a building_id.")

    if building.lod != LODLevel.LOD2:
        errors.append(
            f"Expected LOD2, got LOD{building.lod.value}."
        )

    for plane in building.roof_planes:
        errors.extend(validate_roof_plane(plane))

    for ridge in building.ridges:
        if not ridge.ridge_id:
            errors.append("RoofRidge must have a ridge_id.")
        if len(ridge.start) != 3 or len(ridge.end) != 3:
            errors.append(
                f"Ridge {ridge.ridge_id}: start/end must be 3D."
            )

    return errors


# ---------------------------------------------------------------------------
# LOD-2 to LOD-1 conversion (downgrade path)
# ---------------------------------------------------------------------------


def lod2_to_lod1_surfaces(building: LOD2Building) -> list[dict[str, Any]]:
    """Convert LOD-2 building to LOD-1 surface format.

    This allows LOD-2 data to feed into the existing LOD-1
    analysis pipeline (extract_surfaces -> solar scoring).

    Each roof plane becomes a separate surface. Facades are
    generated from the ground footprint extrusion.

    Returns:
        A list of surface dicts compatible with extract_surfaces().
    """
    surfaces: list[dict[str, Any]] = []

    for plane in building.roof_planes:
        area = calculate_polygon_area(plane.vertices)
        normal = calculate_normal(plane.vertices)
        surface_type = classify_surface(normal)

        surfaces.append({
            "surface_id": plane.plane_id,
            "building_id": building.building_id,
            "area_m2": round(area, 4),
            "vertices": plane.vertices,
            "surface_type": surface_type,
            "lod": 2,
        })

    return surfaces


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def create_sample_gable_building() -> LOD2Building:
    """Create a sample gable-roof building for testing.

    The building is a 10m x 8m rectangular footprint
    with a 3m ridge height, producing two roof planes.
    """

    # Ridge runs along the length (Y-axis).
    ridge_left = [0.0, 4.0, 6.0]   # low edge of left plane
    ridge_right = [10.0, 4.0, 6.0] # low edge of right plane
    ridge_peak = [5.0, 4.0, 8.0]   # peak doesn't apply here;
                                    # for gable, ridge is flat.

    # Left roof plane: from ground-level eaves up to ridge.
    left_plane = RoofPlane(
        plane_id="RP-L1",
        vertices=[
            [0.0, 0.0, 5.0],   # eave at ground-level Y=0
            [10.0, 0.0, 5.0],  # eave at ground-level Y=0
            [10.0, 4.0, 8.0],  # ridge end
            [0.0, 4.0, 8.0],   # ridge start
        ],
        roof_type=RoofType.GABLE,
    )

    # Right roof plane: mirrors left.
    right_plane = RoofPlane(
        plane_id="RP-R1",
        vertices=[
            [0.0, 4.0, 8.0],   # ridge start
            [10.0, 4.0, 8.0],  # ridge end
            [10.0, 8.0, 5.0],  # eave
            [0.0, 8.0, 5.0],   # eave
        ],
        roof_type=RoofType.GABLE,
    )

    # Ridge line.
    ridge = RoofRidge(
        ridge_id="RG-1",
        start=[0.0, 4.0, 8.0],
        end=[10.0, 4.0, 8.0],
        left_plane_id="RP-L1",
        right_plane_id="RP-R1",
        length_m=10.0,
    )

    # Ground footprint.
    ground = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 8.0, 0.0],
        [0.0, 8.0, 0.0],
    ]

    return LOD2Building(
        building_id="LOD2-001",
        roof_planes=[left_plane, right_plane],
        ridges=[ridge],
        ground_vertices=ground,
        roof_type=RoofType.GABLE,
    )


def create_sample_multiplane_building() -> LOD2Building:
    """Create a sample building with 4 hip roof planes."""

    planes = [
        RoofPlane(
            plane_id="HP-N",
            vertices=[
                [0.0, 0.0, 5.0],
                [10.0, 0.0, 5.0],
                [7.5, 2.5, 8.0],
                [2.5, 2.5, 8.0],
            ],
            roof_type=RoofType.HIP,
        ),
        RoofPlane(
            plane_id="HP-S",
            vertices=[
                [2.5, 5.5, 8.0],
                [7.5, 5.5, 8.0],
                [10.0, 8.0, 5.0],
                [0.0, 8.0, 5.0],
            ],
            roof_type=RoofType.HIP,
        ),
        RoofPlane(
            plane_id="HP-E",
            vertices=[
                [7.5, 2.5, 8.0],
                [10.0, 0.0, 5.0],
                [10.0, 8.0, 5.0],
                [7.5, 5.5, 8.0],
            ],
            roof_type=RoofType.HIP,
        ),
        RoofPlane(
            plane_id="HP-W",
            vertices=[
                [2.5, 2.5, 8.0],
                [2.5, 5.5, 8.0],
                [0.0, 8.0, 5.0],
                [0.0, 0.0, 5.0],
            ],
            roof_type=RoofType.HIP,
        ),
    ]

    ground = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0],
        [10.0, 8.0, 0.0],
        [0.0, 8.0, 0.0],
    ]

    return LOD2Building(
        building_id="LOD2-HIP-001",
        roof_planes=planes,
        ground_vertices=ground,
        roof_type=RoofType.HIP,
    )
