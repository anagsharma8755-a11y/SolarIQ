"""Shading and obstruction analysis interface.

This module defines the extensible architecture for future
shading analysis.  It is intentionally a lightweight service
interface — no expensive ray tracing is implemented unless
justified by a concrete use case.

Planned capabilities:
- Building-to-building shading analysis
- Horizon obstruction estimation
- Roof obstruction mapping (vents, HVAC, etc.)
- Surrounding building context

Design principles:
- Each analysis function returns a simple dict result.
- Heavy computation is deferred to implementations.
- The interface is stable; implementations may evolve.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Sequence

from backend.geometry.calculations import Vector3


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ShadingType(str, enum.Enum):
    """Classification of shading source."""

    BUILDING = "building"
    HORIZON = "horizon"
    ROOF_OBSTRUCTION = "roof_obstruction"
    VEGETATION = "vegetation"
    TERRAIN = "terrain"


class ObstructionSeverity(str, enum.Enum):
    """How severely an obstruction affects solar access."""

    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ShadingSource:
    """A single source of potential shading.

    Attributes:
        source_id: Unique identifier.
        shading_type: Classification of the source.
        vertices: 3D vertices defining the obstruction geometry.
        height_m: Maximum height of the obstruction above ground.
        distance_m: Approximate distance to the target surface.
    """

    source_id: str
    shading_type: ShadingType
    vertices: list[list[float]] = field(default_factory=list)
    height_m: float = 0.0
    distance_m: float = 0.0


@dataclass
class ShadingResult:
    """Result of a shading analysis for one surface.

    Attributes:
        surface_id: The analyzed surface.
        has_shading: Whether any shading was detected.
        sources: List of detected shading sources.
        severity: Overall shading severity.
        estimated_shading_fraction: Fraction of the surface
            that is shaded (0.0 = no shade, 1.0 = fully shaded).
    """

    surface_id: str
    has_shading: bool = False
    sources: list[ShadingSource] = field(default_factory=list)
    severity: ObstructionSeverity = ObstructionSeverity.NONE
    estimated_shading_fraction: float = 0.0


# ---------------------------------------------------------------------------
# Analysis interface
# ---------------------------------------------------------------------------


class ShadingAnalyzer:
    """Extensible interface for shading/obstruction analysis.

    This is the entry point for all shading computations.
    Implementations can range from simple distance-based
    heuristics to full ray-tracing engines.

    Usage::

        analyzer = ShadingAnalyzer()
        result = analyzer.analyze_surface(
            surface_id="S001",
            surface_vertices=[[0,0,10], [10,0,10], [10,10,10], [0,10,10]],
            shading_sources=[...],
        )
    """

    def __init__(
        self,
        max_shading_distance_m: float = 200.0,
        min_height_threshold_m: float = 1.0,
    ):
        self.max_shading_distance_m = max_shading_distance_m
        self.min_height_threshold_m = min_height_threshold_m

    def analyze_surface(
        self,
        surface_id: str,
        surface_vertices: Sequence[Vector3],
        shading_sources: Sequence[ShadingSource] | None = None,
    ) -> ShadingResult:
        """Analyze shading for a single surface.

        Currently implements a simple proximity + height
        heuristic.  Future versions can plug in ray tracing
        or solar position models.

        Args:
            surface_id: ID of the surface to analyze.
            surface_vertices: 3D vertices of the surface.
            shading_sources: Potential shading obstructions.

        Returns:
            A ShadingResult with severity and estimated fraction.
        """
        if not shading_sources:
            return ShadingResult(surface_id=surface_id)

        # Compute surface centroid for distance estimation.
        if surface_vertices:
            xs = [v[0] for v in surface_vertices]
            ys = [v[1] for v in surface_vertices]
            zs = [v[2] for v in surface_vertices]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            cz = sum(zs) / len(zs)
        else:
            return ShadingResult(surface_id=surface_id)

        detected: list[ShadingSource] = []

        for source in shading_sources:
            if source.height_m < self.min_height_threshold_m:
                continue

            # Simple distance check.
            if source.distance_m > self.max_shading_distance_m:
                continue

            # Height must exceed the surface height to cast shade.
            if source.height_m <= cz:
                continue

            detected.append(source)

        if not detected:
            return ShadingResult(surface_id=surface_id)

        # Estimate shading fraction based on distance and height.
        total_shading = 0.0
        for src in detected:
            height_ratio = min(
                (src.height_m - cz) / max(cz, 1.0), 1.0
            )
            distance_ratio = max(
                1.0 - (src.distance_m / self.max_shading_distance_m),
                0.0,
            )
            total_shading += height_ratio * distance_ratio * 0.3

        fraction = min(total_shading, 1.0)

        if fraction < 0.1:
            severity = ObstructionSeverity.MINOR
        elif fraction < 0.3:
            severity = ObstructionSeverity.MODERATE
        else:
            severity = ObstructionSeverity.SEVERE

        return ShadingResult(
            surface_id=surface_id,
            has_shading=True,
            sources=detected,
            severity=severity,
            estimated_shading_fraction=round(fraction, 4),
        )

    def analyze_building(
        self,
        building_id: str,
        surfaces: Sequence[dict[str, Any]],
        shading_sources: Sequence[ShadingSource] | None = None,
    ) -> list[ShadingResult]:
        """Analyze shading for all surfaces of a building.

        Args:
            building_id: Building identifier.
            surfaces: List of surface dicts (from extract_surfaces).
            shading_sources: Potential shading obstructions.

        Returns:
            A list of ShadingResult, one per surface.
        """
        results: list[ShadingResult] = []

        for surface in surfaces:
            sid = surface.get("surface_id", "unknown")
            verts = surface.get("vertices", [])
            result = self.analyze_surface(sid, verts, shading_sources)
            results.append(result)

        return results

    def filter_nearby_sources(
        self,
        sources: Sequence[ShadingSource],
        reference_height: float = 10.0,
    ) -> list[ShadingSource]:
        """Pre-filter shading sources to those that could
        plausibly affect a surface at the given height.

        This is an optimization to avoid running full analysis
        on every source-surface pair.
        """
        filtered: list[ShadingSource] = []
        for src in sources:
            if src.height_m < self.min_height_threshold_m:
                continue
            if src.height_m <= reference_height:
                continue
            if src.distance_m > self.max_shading_distance_m:
                continue
            filtered.append(src)
        return filtered


# ---------------------------------------------------------------------------
# Horizon obstruction (simplified)
# ---------------------------------------------------------------------------


def estimate_horizon_obstruction(
    surface_tilt_deg: float,
    surface_azimuth_deg: float,
    horizon_angles: dict[str, float] | None = None,
) -> float:
    """Estimate horizon obstruction for a surface.

    A simplified model that checks whether the horizon
    elevation angle exceeds the surface tilt, which would
    indicate that distant terrain or structures block
    direct sunlight.

    Args:
        surface_tilt_deg: Surface tilt from horizontal.
        surface_azimuth_deg: Surface compass bearing.
        horizon_angles: Dict mapping compass direction to
            horizon elevation angle in degrees. E.g.
            {"north": 15, "east": 5, "south": 0, "west": 20}.

    Returns:
        Obstruction fraction from 0.0 (clear) to 1.0 (fully blocked).
    """
    if not horizon_angles:
        return 0.0

    # Map azimuth to cardinal direction.
    if surface_azimuth_deg < 45 or surface_azimuth_deg >= 315:
        direction = "north"
    elif 45 <= surface_azimuth_deg < 135:
        direction = "east"
    elif 135 <= surface_azimuth_deg < 225:
        direction = "south"
    else:
        direction = "west"

    horizon_angle = horizon_angles.get(direction, 0.0)

    if horizon_angle <= 0:
        return 0.0

    # If horizon angle exceeds surface tilt, the surface
    # is partially or fully obstructed.
    if horizon_angle >= surface_tilt_deg + 90:
        return 1.0

    if horizon_angle > surface_tilt_deg:
        return min(
            (horizon_angle - surface_tilt_deg) / 90.0,
            1.0,
        )

    return 0.0
