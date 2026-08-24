"""3D geometry calculation primitives for SolarIQ.

Enhancements over the original module:

- Reversed vertex winding detection and correction.
- Degenerate polygon detection (zero-area, collinear).
- Support for triangles, quadrilaterals, and arbitrary planar polygons.
- Centroid and bounding-box computation.
- Clear documentation of coordinate conventions and units.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np


Vector3 = Sequence[float]

# ---------------------------------------------------------------------------
# Batch analysis (single-pass geometry computation)
# ---------------------------------------------------------------------------


def analyze_polygon_batch(
    vertices: Sequence[Vector3],
) -> dict[str, object]:
    """Compute all geometry properties in a single pass.

    This replaces 7 separate function calls with one batch
    operation that converts vertices to numpy arrays only once
    and computes normal, area, tilt, azimuth, surface type,
    centroid, and bounding box together.

    Returns:
        A dict with: normal, area_m2, tilt_deg, azimuth_deg,
        surface_type, centroid, bounding_box, is_degenerate.

    Raises:
        ValueError: If vertices are malformed or degenerate.
    """
    if len(vertices) < 3:
        raise ValueError("At least three vertices are required.")

    # Convert to numpy ONCE for all subsequent operations.
    points = [np.asarray(v, dtype=float) for v in vertices]

    p0 = points[0]
    p1 = points[1]
    p2 = points[2]

    edge1 = p1 - p0
    edge2 = p2 - p0

    normal_raw = np.cross(edge1, edge2)
    magnitude = np.linalg.norm(normal_raw)

    # Degenerate check.
    if magnitude < 1e-10:
        raise ValueError("Surface degenerate: collinear or zero-area vertices.")

    n_hat = normal_raw / magnitude

    # --- Reversed winding check ---
    abs_n = np.abs(n_hat)
    dominant_idx = int(np.argmax(abs_n))
    reversed_winding = bool(n_hat[dominant_idx] < 0)

    if reversed_winding:
        n_hat = -n_hat
        normal_raw = -normal_raw

    normal_list = [float(n_hat[0]), float(n_hat[1]), float(n_hat[2])]

    # --- Tilt ---
    vertical_component = abs(n_hat[2])
    vertical_component = max(-1.0, min(1.0, vertical_component))
    tilt = math.degrees(math.acos(vertical_component))

    # --- Azimuth ---
    horizontal_magnitude = math.hypot(n_hat[0], n_hat[1])
    if horizontal_magnitude < 1e-10:
        azimuth = 0.0
    else:
        azimuth = math.degrees(math.atan2(n_hat[0], n_hat[1]))
        if azimuth < 0:
            azimuth += 360.0

    # --- Surface type ---
    if tilt < 45.0:
        if n_hat[2] > 0:
            surface_type = "roof"
        else:
            surface_type = "ground"
    else:
        surface_type = "facade"

    # --- Polygon area (fan triangulation) ---
    area = 0.0
    for i in range(1, len(points) - 1):
        e1 = points[i] - p0
        e2 = points[i + 1] - p0
        area += 0.5 * float(np.linalg.norm(np.cross(e1, e2)))

    if area <= 0:
        raise ValueError("Surface area must be greater than zero.")

    # --- Centroid ---
    centroid = [float(c) for c in np.mean(points, axis=0)]

    # --- Bounding box ---
    pts_arr = np.array(vertices, dtype=float)
    mins = pts_arr.min(axis=0)
    maxs = pts_arr.max(axis=0)
    bbox = {
        "min_x": float(mins[0]), "min_y": float(mins[1]), "min_z": float(mins[2]),
        "max_x": float(maxs[0]), "max_y": float(maxs[1]), "max_z": float(maxs[2]),
        "width_x": float(maxs[0] - mins[0]),
        "width_y": float(maxs[1] - mins[1]),
        "height_z": float(maxs[2] - mins[2]),
    }

    return {
        "normal": normal_list,
        "area_m2": float(area),
        "tilt_deg": float(tilt),
        "azimuth_deg": float(azimuth),
        "surface_type": surface_type,
        "centroid": centroid,
        "bounding_box": bbox,
        "is_degenerate": False,
        "reversed_winding": reversed_winding,
        "points": points,  # Keep for potential reuse.
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_array(vector: Vector3) -> np.ndarray:
    """Convert a 3D vector to a NumPy array."""

    array = np.asarray(vector, dtype=float)

    if array.shape != (3,):
        raise ValueError(
            "A 3D vector must contain exactly three values."
        )

    return array


def _ensure_ccw_winding(vertices: list[np.ndarray]) -> list[np.ndarray]:
    """Ensure a planar polygon has consistent outward-pointing normal.

    Uses the dominant axis of the cross product (computed from the
    first two edges) to determine the winding reference direction.
    If the cross product points in the negative direction along
    the dominant axis, the vertices are reversed.

    Convention for building geometry:
        - Horizontal surfaces: normal should point upward (z > 0)
        - Vertical surfaces:   normal should point along +X or +Y
        - The dominant axis of the cross product determines the
          expected positive direction.
    """

    if len(vertices) < 3:
        return vertices

    p0 = vertices[0]
    edge1 = vertices[1] - p0
    edge2 = vertices[2] - p0
    normal = np.cross(edge1, edge2)
    magnitude = np.linalg.norm(normal)

    if magnitude < 1e-12:
        return vertices

    n_hat = normal / magnitude

    # Determine the dominant axis of the normal.
    abs_n = np.abs(n_hat)
    dominant_idx = int(np.argmax(abs_n))

    # If the normal points in the negative direction along the
    # dominant axis, the winding is reversed.
    if n_hat[dominant_idx] < 0:
        return list(reversed(vertices))

    return vertices


# ---------------------------------------------------------------------------
# Normal calculation
# ---------------------------------------------------------------------------


def calculate_normal(
    vertices: Sequence[Vector3],
) -> list[float]:
    """Calculate the unit surface normal.

    Uses the first three vertices to define the surface plane.
    The normal direction is determined by the cross product of
    the first two edges (edge1 x edge2).  This follows the
    right-hand rule applied to counter-clockwise winding.

    The returned normal is always a unit vector.

    Raises:
        ValueError: If fewer than 3 vertices or vertices are collinear.
    """

    if len(vertices) < 3:
        raise ValueError(
            "At least three vertices are required."
        )

    p0 = _to_array(vertices[0])
    p1 = _to_array(vertices[1])
    p2 = _to_array(vertices[2])

    edge1 = p1 - p0
    edge2 = p2 - p0

    normal = np.cross(edge1, edge2)

    magnitude = np.linalg.norm(normal)

    if magnitude < 1e-12:
        raise ValueError(
            "Surface vertices are collinear."
        )

    unit_normal = normal / magnitude

    return unit_normal.tolist()


# ---------------------------------------------------------------------------
# Area calculation
# ---------------------------------------------------------------------------


def calculate_polygon_area(
    vertices: Sequence[Vector3],
) -> float:
    """Calculate the area of a planar 3D polygon.

    The polygon is triangulated from the first vertex (fan
    triangulation).  This works correctly for convex and
    simple concave polygons.

    Units: square units of the input vertex coordinates.
    If vertices are in metres, the area is in square metres.

    Raises:
        ValueError: If fewer than 3 vertices or area is zero.
    """

    if len(vertices) < 3:
        raise ValueError(
            "At least three vertices are required."
        )

    points = [
        _to_array(vertex)
        for vertex in vertices
    ]

    area = 0.0
    origin = points[0]

    for i in range(1, len(points) - 1):

        edge1 = points[i] - origin
        edge2 = points[i + 1] - origin

        triangle_area = 0.5 * np.linalg.norm(
            np.cross(edge1, edge2)
        )

        area += triangle_area

    if area <= 0:
        raise ValueError(
            "Surface area must be greater than zero."
        )

    return float(area)


def calculate_polygon_area_signed(
    vertices: Sequence[Vector3],
) -> float:
    """Calculate signed area of a planar 3D polygon.

    Uses the dominant axis of the cross product (from the first
    two edges) as the fixed reference direction.  Returns a
    positive value when vertices are ordered so the cross product
    points in the positive direction along that axis.

    Useful for detecting reversed winding order.
    """

    if len(vertices) < 3:
        raise ValueError(
            "At least three vertices are required."
        )

    points = [_to_array(v) for v in vertices]

    p0 = points[0]
    edge1 = points[1] - p0
    edge2 = points[2] - p0
    normal = np.cross(edge1, edge2)
    magnitude = np.linalg.norm(normal)

    if magnitude < 1e-12:
        return 0.0

    n_hat = normal / magnitude

    # Build a fixed reference direction along the dominant axis.
    abs_n = np.abs(n_hat)
    dominant_idx = int(np.argmax(abs_n))
    ref = np.zeros(3)
    ref[dominant_idx] = 1.0

    signed_area = 0.0
    for i in range(1, len(points) - 1):
        e1 = points[i] - p0
        e2 = points[i + 1] - p0
        cross = np.cross(e1, e2)
        signed_area += np.dot(cross, ref)

    return float(signed_area * 0.5)


def is_reversed_winding(
    vertices: Sequence[Vector3],
) -> bool:
    """Return True if the winding order is reversed.

    A polygon is considered "reversed" if the cross product of
    the first two edges points in the negative direction along
    the dominant axis of the normal.

    Convention:
        - Horizontal surfaces: reversed if normal points downward.
        - Vertical surfaces:   reversed if normal points along -X/-Y.
    """

    if len(vertices) < 3:
        return False

    points = [_to_array(v) for v in vertices]

    p0 = points[0]
    edge1 = points[1] - p0
    edge2 = points[2] - p0
    normal = np.cross(edge1, edge2)

    magnitude = np.linalg.norm(normal)

    if magnitude < 1e-12:
        return False

    n_hat = normal / magnitude

    # Check the dominant axis.
    abs_n = np.abs(n_hat)
    dominant_idx = int(np.argmax(abs_n))

    return n_hat[dominant_idx] < 0


# ---------------------------------------------------------------------------
# Degenerate polygon detection
# ---------------------------------------------------------------------------


def is_degenerate_polygon(
    vertices: Sequence[Vector3],
    tolerance: float = 1e-10,
) -> bool:
    """Return True if the polygon is degenerate.

    A polygon is degenerate if:
    - It has fewer than 3 vertices.
    - Its area is zero (all vertices are collinear).
    - Its normal cannot be computed.
    """

    if len(vertices) < 3:
        return True

    points = [_to_array(v) for v in vertices]

    p0 = points[0]
    if len(points) >= 3:
        edge1 = points[1] - p0
        edge2 = points[2] - p0
        normal = np.cross(edge1, edge2)
        if np.linalg.norm(normal) < tolerance:
            return True

    area = 0.0
    origin = points[0]
    for i in range(1, len(points) - 1):
        e1 = points[i] - origin
        e2 = points[i + 1] - origin
        area += 0.5 * np.linalg.norm(np.cross(e1, e2))

    return area < tolerance


# ---------------------------------------------------------------------------
# Centroid and bounding box
# ---------------------------------------------------------------------------


def calculate_centroid(
    vertices: Sequence[Vector3],
) -> list[float]:
    """Calculate the 3D centroid (arithmetic mean) of the polygon.

    Returns:
        A list [cx, cy, cz].
    """

    if not vertices:
        raise ValueError(
            "At least one vertex is required."
        )

    points = [_to_array(v) for v in vertices]
    centroid = np.mean(points, axis=0)
    return centroid.tolist()


def calculate_bounding_box(
    vertices: Sequence[Vector3],
) -> dict[str, float]:
    """Calculate the axis-aligned bounding box.

    Returns:
        A dict with min_x, min_y, min_z, max_x, max_y, max_z,
        width_x, width_y, height_z.
    """

    if not vertices:
        raise ValueError(
            "At least one vertex is required."
        )

    points = np.array(vertices, dtype=float)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)

    return {
        "min_x": float(mins[0]),
        "min_y": float(mins[1]),
        "min_z": float(mins[2]),
        "max_x": float(maxs[0]),
        "max_y": float(maxs[1]),
        "max_z": float(maxs[2]),
        "width_x": float(maxs[0] - mins[0]),
        "width_y": float(maxs[1] - mins[1]),
        "height_z": float(maxs[2] - mins[2]),
    }


# ---------------------------------------------------------------------------
# Tilt and azimuth
# ---------------------------------------------------------------------------


def calculate_tilt(
    normal: Vector3,
) -> float:
    """Calculate surface tilt in degrees.

    Convention:
        0 deg = horizontal (normal pointing straight up)
        90 deg = vertical (normal pointing horizontally)
    """

    n = _to_array(normal)

    magnitude = np.linalg.norm(n)

    if magnitude == 0:
        raise ValueError(
            "Normal vector cannot have zero magnitude."
        )

    unit_normal = n / magnitude

    vertical_component = abs(unit_normal[2])

    vertical_component = max(
        -1.0,
        min(1.0, vertical_component),
    )

    tilt = math.degrees(
        math.acos(vertical_component)
    )

    return float(tilt)


def calculate_azimuth(
    normal: Vector3,
) -> float:
    """Calculate surface azimuth in degrees.

    Coordinate convention:
        X = East
        Y = North
        Z = Up

    Azimuth:
        0 deg   = North
        90 deg  = East
        180 deg = South
        270 deg = West

    Horizontal surfaces do not have a meaningful compass
    direction, so 0.0 is returned.
    """

    n = _to_array(normal)

    horizontal_magnitude = math.hypot(
        n[0],
        n[1],
    )

    if horizontal_magnitude < 1e-10:
        return 0.0

    azimuth = math.degrees(
        math.atan2(
            n[0],
            n[1],
        )
    )

    if azimuth < 0:
        azimuth += 360.0

    return float(azimuth)


# ---------------------------------------------------------------------------
# Surface classification
# ---------------------------------------------------------------------------


def classify_surface(
    normal: Vector3,
) -> str:
    """Classify a surface using its normal.

    Classification:
        Tilt < 45 deg and upward   -> roof
        Tilt < 45 deg and downward -> ground
        Tilt >= 45 deg             -> facade
    """

    n = _to_array(normal)

    magnitude = np.linalg.norm(n)

    if magnitude == 0:
        raise ValueError(
            "Normal vector cannot have zero magnitude."
        )

    unit_normal = n / magnitude

    vertical_component = unit_normal[2]

    tilt = calculate_tilt(unit_normal)

    if tilt < 45.0:

        if vertical_component > 0:
            return "roof"

        return "ground"

    return "facade"


# ---------------------------------------------------------------------------
# Planarity check
# ---------------------------------------------------------------------------


def is_planar(
    vertices: Sequence[Vector3],
    tolerance: float = 1e-6,
) -> bool:
    """Check whether all vertices lie on a single plane.

    Uses the normal defined by the first three vertices,
    then checks that every remaining vertex is within
    tolerance distance from that plane.
    """

    if len(vertices) < 3:
        return True

    points = [_to_array(v) for v in vertices]

    p0 = points[0]
    edge1 = points[1] - p0
    edge2 = points[2] - p0
    normal = np.cross(edge1, edge2)
    magnitude = np.linalg.norm(normal)

    if magnitude < 1e-12:
        return True

    n_hat = normal / magnitude

    for point in points[3:]:
        dist = abs(np.dot(point - p0, n_hat))
        if dist > tolerance:
            return False

    return True


# ---------------------------------------------------------------------------
# Signed winding normalisation (public API)
# ---------------------------------------------------------------------------


def normalise_winding(
    vertices: Sequence[Vector3],
) -> list[list[float]]:
    """Return a copy of vertices with consistent CCW winding.

    This is a safe entry point that detects reversed winding
    and corrects it before normal/solar calculations.
    """

    if len(vertices) < 3:
        return [list(v) for v in vertices]

    points = [_to_array(v) for v in vertices]
    fixed = _ensure_ccw_winding(points)
    return [[float(c) for c in v] for v in fixed]
