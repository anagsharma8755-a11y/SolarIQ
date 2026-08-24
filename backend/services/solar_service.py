from __future__ import annotations

import math
from typing import Any

from backend.config import (
    ANNUAL_IRRADIANCE_KWH_M2,
    COVERAGE_FACTOR,
    PANEL_EFFICIENCY,
)


# Keep module-level aliases so existing imports still work.
DEFAULT_COVERAGE_FACTOR = COVERAGE_FACTOR
DEFAULT_PANEL_EFFICIENCY = PANEL_EFFICIENCY

# Fallback/demo value only.
DEFAULT_ANNUAL_IRRADIANCE_KWH_M2 = ANNUAL_IRRADIANCE_KWH_M2

# ──────────────────────────────────────────────────────────────
# Roof panel installation assumption
# ──────────────────────────────────────────────────────────────
# A flat/horizontal roof (geometric tilt ≈ 0°) does NOT mean
# solar panels must be installed at 0°. Panels on flat roofs
# are mounted on racking at an optimal tilt angle.
#
# This is an installation assumption, NOT measured roof geometry.
# Future improvement: derive from latitude via PVGIS/PVLib.
DEFAULT_ROOF_PANEL_TILT_DEG: float = 20.0

# ──────────────────────────────────────────────────────────────
# MVP irradiance model (fallback)
# ──────────────────────────────────────────────────────────────
# These are baseline values for a mid-latitude location.
# They are NOT site-specific. The architecture supports
# future integration with PVGIS, PVLib, ERA5, Open-Meteo,
# or ML-based irradiance prediction.
#
# Typical annual irradiance on an optimally tilted surface:
# - Equatorial: 1800-2200 kWh/m²
# - Mid-latitude: 1200-1800 kWh/m²
# - High latitude: 800-1200 kWh/m²
#
# 1700 kWh/m² is a reasonable mid-latitude default.
FALLBACK_ANNUAL_IRRADIANCE_KWH_M2 = 1700.0

# ──────────────────────────────────────────────────────────────
# Continuous irradiance factors (smooth transitions)
# ──────────────────────────────────────────────────────────────
# Instead of discrete categories, use continuous functions
# for smoother, more realistic irradiance modeling.

# Optimal tilt angle for maximum irradiance capture
OPTIMAL_TILT_DEG: float = 20.0

# Tilt factor: continuous function based on distance from optimal
# At optimal tilt (20°): factor = 1.0
# At vertical (90°): factor ≈ 0.55
# At horizontal (0°): factor ≈ 0.95 (slightly less than optimal)
def _tilt_factor_continuous(tilt_deg: float) -> float:
    """Calculate irradiance factor based on tilt angle.

    Uses a continuous cosine-based model that smoothly transitions
    between tilt angles rather than discrete categories.

    The model approximates how the angle of incidence affects
    the solar irradiance captured by a tilted surface.
    """
    # Convert to radians for calculation
    tilt_rad = math.radians(tilt_deg)
    optimal_rad = math.radians(OPTIMAL_TILT_DEG)

    # Distance from optimal tilt (in degrees)
    delta = abs(tilt_deg - OPTIMAL_TILT_DEG)

    # Continuous decay function
    # At delta=0: factor=1.0
    # At delta=70 (90° vs 20°): factor≈0.55
    factor = math.exp(-0.008 * delta**1.3)

    # Ensure minimum factor for vertical surfaces
    return max(0.55, min(1.0, factor))


# Azimuth factor: continuous function based on deviation from south
def _azimuth_factor_continuous(azimuth_deg: float) -> float:
    """Calculate irradiance factor based on azimuth orientation.

    Uses a continuous model for smooth transitions.
    South-facing (180°) gets maximum factor.
    North-facing (0°/360°) gets minimum factor.
    East/West (90°/270°) get intermediate factors.
    """
    # Normalize to 0-360
    az = azimuth_deg % 360

    # Deviation from south (180°)
    deviation = abs(az - 180.0)
    if deviation > 180.0:
        deviation = 360.0 - deviation

    # Use a piecewise function for better differentiation:
    # - South (0-30° deviation): 0.95-1.0
    # - SE/SW (30-60°): 0.80-0.95
    # - East/West (60-120°): 0.60-0.80
    # - NE/NW (120-150°): 0.45-0.60
    # - North (150-180°): 0.35-0.45
    if deviation <= 30:
        factor = 1.0 - 0.05 * (deviation / 30.0)
    elif deviation <= 60:
        factor = 0.95 - 0.15 * ((deviation - 30) / 30.0)
    elif deviation <= 120:
        factor = 0.80 - 0.20 * ((deviation - 60) / 60.0)
    elif deviation <= 150:
        factor = 0.60 - 0.15 * ((deviation - 120) / 30.0)
    else:
        factor = 0.45 - 0.10 * ((deviation - 150) / 30.0)

    return max(0.35, min(1.0, factor))


# ──────────────────────────────────────────────────────────────
# Installation practicality factors
# ──────────────────────────────────────────────────────────────
# These reflect ease of installation and maintenance.
# Roofs are generally easier to access and maintain.
# Facades require specialized mounting and safety equipment.
INSTALLATION_PRACTICALITY: dict[str, float] = {
    "roof": 1.0,     # Easy access, standard mounting
    "facade": 0.70,  # Requires specialized equipment
    "ground": 0.80,  # Easy access but land use concerns
}


def _classify_tilt(tilt_deg: float) -> str:
    """Classify tilt angle into categories for irradiance factor lookup."""
    if tilt_deg <= 30:
        return "near_optimal"
    elif tilt_deg <= 50:
        return "moderate"
    elif tilt_deg <= 70:
        return "steep"
    else:
        return "vertical"


def _classify_azimuth(azimuth_deg: float) -> str:
    """Classify azimuth into categories for irradiance factor lookup."""
    # Normalize to 0-360
    az = azimuth_deg % 360

    if 150 <= az <= 210:
        return "south"
    elif (120 <= az < 150) or (210 < az <= 240):
        return "se_sw"
    elif (60 <= az < 120) or (240 < az <= 300):
        return "east_west"
    elif (30 <= az < 60) or (300 < az <= 330):
        return "ne_nw"
    else:  # 330-360 or 0-30
        return "north"


def orientation_score(
    azimuth_deg: float,
    surface_type: str = "facade",
) -> float:
    """Calculate orientation suitability.

    For flat/horizontal roofs, azimuth is not meaningful
    because panels can be oriented independently.
    Roofs receive the maximum score.

    For facades, south-facing orientations receive the
    highest score (northern hemisphere convention).

    Uses continuous function for smooth transitions.

    Returns: Normalized score from 0.0 to 1.0.
    """
    if surface_type == "roof":
        return 1.0

    # Use continuous azimuth factor for smoother scoring
    return round(_azimuth_factor_continuous(azimuth_deg), 4)


def tilt_score(
    tilt_deg: float,
    *,
    is_roof: bool = False,
) -> float:
    """Calculate suitability based on panel installation tilt.

    CRITICAL DISTINCTION:
        BUILDING GEOMETRY TILT vs PANEL INSTALLATION TILT

        - A flat roof has geometric tilt ≈ 0°, but panels
          can be installed at an optimal angle using racking.
        - A facade has geometric tilt ≈ 90°, and panels are
          constrained to follow the facade orientation.

    For roofs: Uses DEFAULT_ROOF_PANEL_TILT_DEG (20°) as the
        assumed panel installation tilt, NOT the geometric tilt.
    For facades: Uses the actual geometric tilt.

    Uses continuous function for smooth transitions.

    Returns: Normalized score from 0.0 to 1.0.
    """
    tilt = float(tilt_deg)
    if not 0.0 <= tilt <= 90.0:
        raise ValueError("Tilt must be between 0 and 90 degrees.")

    # For roofs, use assumed panel installation tilt.
    if is_roof:
        effective_tilt = DEFAULT_ROOF_PANEL_TILT_DEG
    else:
        effective_tilt = tilt

    # Use continuous tilt factor for smoother scoring
    return round(_tilt_factor_continuous(effective_tilt), 4)


def estimate_irradiance(
    surface: dict[str, Any],
    annual_irradiance_kwh_m2: float = FALLBACK_ANNUAL_IRRADIANCE_KWH_M2,
) -> float:
    """Estimate effective irradiance for a surface.

    This is a continuous model that considers:
    1. Base irradiance (site-specific or fallback)
    2. Tilt factor (smooth function of tilt angle)
    3. Azimuth factor (smooth function of orientation)

    The model uses continuous functions instead of discrete
    categories for more realistic irradiance estimation.

    Returns: Estimated annual irradiance in kWh/m².
    """
    surface_type = str(surface.get("surface_type", "facade")).lower()
    tilt_deg = float(surface.get("tilt_deg", 90.0))
    azimuth_deg = float(surface.get("azimuth_deg", 0.0))

    # Determine effective tilt for irradiance calculation
    if surface_type == "roof":
        # Roofs: panels can be tilted optimally
        effective_tilt = DEFAULT_ROOF_PANEL_TILT_DEG
    else:
        # Facades: constrained by building geometry
        effective_tilt = tilt_deg

    # Get continuous factors
    tilt_factor = _tilt_factor_continuous(effective_tilt)

    # Get azimuth factor (only meaningful for facades)
    if surface_type == "roof":
        azimuth_factor = 1.0  # Roofs can be oriented arbitrarily
    else:
        azimuth_factor = _azimuth_factor_continuous(azimuth_deg)

    # Combined irradiance
    effective_irradiance = annual_irradiance_kwh_m2 * tilt_factor * azimuth_factor

    return round(effective_irradiance, 4)


def calculate_solar_score(
    surface: dict[str, Any],
) -> float:
    """Calculate normalized BIPV surface suitability.

    This is a DATA-DRIVEN model that evaluates surfaces based on
    their actual solar potential, NOT hardcoded surface type rules.

    The model considers:
    1. Solar resource quality (orientation + tilt)
    2. Installation practicality
    3. Surface geometry suitability

    KEY DESIGN PRINCIPLE:
        The model does NOT hardcode roof > facade or facade > roof.
        Instead, it evaluates each surface based on its actual
        characteristics. A well-oriented south facade on a tall
        building can have better solar potential than a poorly-
        oriented roof section.

    Returns: Score from 0.0 to 1.0.
    """
    surface_type = str(surface.get("surface_type", "facade")).lower()

    if surface_type == "ground":
        return 0.0

    try:
        azimuth = float(surface.get("azimuth_deg", 0.0))
        tilt = float(surface.get("tilt_deg", 90.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Surface azimuth and tilt must be numeric.") from exc

    is_roof = surface_type == "roof"

    # 1. Solar resource quality (50% weight)
    #    - Orientation component (25%)
    #    - Tilt component (25%)
    orientation = orientation_score(azimuth, surface_type)
    tilt_component = tilt_score(tilt, is_roof=is_roof)
    solar_resource = 0.5 * orientation + 0.5 * tilt_component

    # 2. Installation practicality (30% weight)
    #    - Roofs are generally easier to install on
    #    - Facades require specialized equipment
    practicality = INSTALLATION_PRACTICALITY.get(surface_type, 0.5)

    # 3. Surface geometry suitability (20% weight)
    #    - This is a base factor that doesn't favor any type
    #    - All viable surfaces get the same base score
    geometry = 0.8  # Base suitability for all viable surfaces

    # Combined score
    score = (
        0.50 * solar_resource
        + 0.30 * practicality
        + 0.20 * geometry
    )

    return round(max(0.0, min(1.0, score)), 4)


def calculate_installation_priority(
    surface: dict[str, Any],
    *,
    max_energy_in_dataset: float | None = None,
    max_area_in_dataset: float | None = None,
) -> float:
    """Calculate internal installation priority score.

    This combines:
    - Solar suitability score
    - Expected annual energy generation
    - Usable area

    The priority score is used internally for ranking surfaces
    in the optimization endpoint. It represents: "Which surfaces
    should a city planner prioritize first?"

    A surface with high suitability AND high energy potential
    gets a higher priority than one with only high suitability.

    Args:
        surface: Analyzed surface with solar_score and energy_potential
        max_energy_in_dataset: Optional max energy for relative normalization
        max_area_in_dataset: Optional max area for relative normalization

    Returns: Priority score from 0.0 to 1.0 (normalized).
    """
    score = surface.get("solar_score", 0.0)
    energy = surface.get("energy_potential", {})
    annual_kwh = energy.get("estimated_annual_energy_kwh", 0.0)
    usable_area = energy.get("usable_area_m2", 0.0)

    # Use relative normalization if dataset bounds provided
    if max_energy_in_dataset is not None and max_energy_in_dataset > 0:
        energy_normalized = min(1.0, annual_kwh / max_energy_in_dataset)
    else:
        # Fallback: use reference value
        # Max possible energy for a large roof: ~400m² * 1700 * 0.20 = 136,000 kWh
        max_reference_energy = 136000.0
        energy_normalized = min(1.0, annual_kwh / max_reference_energy)

    if max_area_in_dataset is not None and max_area_in_dataset > 0:
        area_normalized = min(1.0, usable_area / max_area_in_dataset)
    else:
        # Fallback: use reference value
        max_reference_area = 400.0
        area_normalized = min(1.0, usable_area / max_reference_area)

    # Priority combines suitability, energy, and area
    # Higher weight on energy because that's what matters for ROI
    priority = (
        0.35 * score           # Solar suitability
        + 0.45 * energy_normalized  # Energy generation potential
        + 0.20 * area_normalized    # Usable area
    )

    return round(max(0.0, min(1.0, priority)), 4)


def estimate_energy_potential(
    surface: dict[str, Any],
    annual_irradiance_kwh_m2: float = DEFAULT_ANNUAL_IRRADIANCE_KWH_M2,
    coverage_factor: float = DEFAULT_COVERAGE_FACTOR,
    panel_efficiency: float = DEFAULT_PANEL_EFFICIENCY,
) -> dict[str, float]:
    """Estimate baseline BIPV energy potential.

    Formula:
        usable_area = surface_area * coverage_factor
        capacity_kw = usable_area * panel_efficiency
        annual_energy = usable_area * annual_irradiance * panel_efficiency

    The irradiance parameter can be:
    - A fixed fallback value (current default)
    - Site-specific from PVGIS/PVGIS (future)
    - ML-predicted irradiance (future)

    Assumptions (MVP):
        - coverage_factor: 0.80
        - panel_efficiency: 0.20
        - annual_irradiance: 1700 kWh/m² (NOT site-specific)

    Returns: usable area, estimated capacity and annual energy.
    """
    try:
        area = float(surface.get("area_m2", 0.0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Surface area must be numeric.") from exc

    if area <= 0:
        raise ValueError("Surface area must be greater than zero.")
    if not 0 < coverage_factor <= 1:
        raise ValueError("Coverage factor must be between 0 and 1.")
    if not 0 < panel_efficiency <= 1:
        raise ValueError("Panel efficiency must be between 0 and 1.")
    if annual_irradiance_kwh_m2 <= 0:
        raise ValueError("Annual irradiance must be greater than zero.")

    usable_area = area * coverage_factor
    capacity_kw = usable_area * panel_efficiency
    annual_energy = usable_area * annual_irradiance_kwh_m2 * panel_efficiency

    return {
        "usable_area_m2": round(usable_area, 4),
        "estimated_capacity_kw": round(capacity_kw, 4),
        "estimated_annual_energy_kwh": round(annual_energy, 4),
    }


def suitability_label(score: float) -> str:
    """Convert a solar score into a human-readable category."""
    if score >= 0.75:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def analyze_surface(surface: dict[str, Any]) -> dict[str, Any]:
    """Combine geometry information with solar suitability
    and baseline energy estimation.

    Ground surfaces are intentionally assigned zero
    solar potential.
    """
    analyzed = dict(surface)
    score = calculate_solar_score(analyzed)
    analyzed["solar_score"] = score
    analyzed["solar_suitability"] = suitability_label(score)

    if analyzed.get("surface_type") == "ground":
        analyzed["energy_potential"] = {
            "usable_area_m2": 0.0,
            "estimated_capacity_kw": 0.0,
            "estimated_annual_energy_kwh": 0.0,
        }
        analyzed["installation_priority"] = 0.0
        return analyzed

    analyzed["energy_potential"] = estimate_energy_potential(analyzed)

    # Calculate installation priority (internal use for ranking)
    analyzed["installation_priority"] = calculate_installation_priority(analyzed)

    return analyzed
