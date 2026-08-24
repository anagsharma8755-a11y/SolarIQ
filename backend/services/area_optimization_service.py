"""Capacity and budget-constrained BIPV optimization engine.

Given an area analysis and user constraints (e.g. "Install up to 500 kW"),
this service calculates the optimal subset of surfaces that maximizes clean
energy generation while strictly respecting the capacity ceiling.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Standard grid emissions factor (kg CO2 / kWh)
GRID_EMISSIONS_FACTOR_KG_KWH = 0.82


class AreaOptimizationService:
    """Optimizes solar deployment subject to capacity and suitability constraints."""

    def optimize_deployment(
        self,
        ranked_surfaces: list[dict[str, Any]],
        max_capacity_kw: float | None = None,
        min_solar_score: float = 0.40,
        allowed_surface_types: list[str] | None = None,
        target_metric: str = "max_energy",
    ) -> dict[str, Any]:
        """Select the highest-value surfaces up to max_capacity_kw.

        Args:
            ranked_surfaces: Ranked list of surface candidates from AreaAnalysisService.
            max_capacity_kw: Target maximum installed capacity in kW (e.g. 500 kW).
            min_solar_score: Minimum solar score threshold (0.0 - 1.0).
            allowed_surface_types: Filter by surface types (e.g. ["roof", "facade"]).
            target_metric: "max_energy" or "max_capacity" or "balanced".

        Returns:
            Optimization summary, selected surfaces, phased deployment strategy,
            and unselected candidates.
        """
        allowed_types = set(allowed_surface_types) if allowed_surface_types else {"roof", "facade"}

        # 1. Filter candidates
        filtered: list[dict[str, Any]] = []
        for s in ranked_surfaces:
            if s.get("surface_type") not in allowed_types:
                continue
            if s.get("solar_score", 0.0) < min_solar_score:
                continue
            if s.get("usable_area_m2", 0.0) <= 0.0:
                continue
            filtered.append(s)

        # 2. Sort by energy yield per unit capacity (energy density) or composite score
        if target_metric == "max_energy":
            # Sort by annual energy / capacity ratio (efficiency), then composite score
            filtered.sort(
                key=lambda x: (
                    x["estimated_annual_energy_kwh"] / max(0.1, x["estimated_capacity_kw"]),
                    x.get("composite_score", 0.0),
                ),
                reverse=True,
            )
        else:
            # Sort by composite score
            filtered.sort(key=lambda x: x.get("composite_score", 0.0), reverse=True)

        selected: list[dict[str, Any]] = []
        unselected: list[dict[str, Any]] = []

        running_capacity = 0.0
        running_energy = 0.0
        running_usable_area = 0.0

        for candidate in filtered:
            cand_cap = candidate.get("estimated_capacity_kw", 0.0)

            # If capacity limit is specified, check constraint
            if max_capacity_kw is not None:
                if running_capacity + cand_cap <= max_capacity_kw:
                    selected.append(candidate)
                    running_capacity += cand_cap
                    running_energy += candidate.get("estimated_annual_energy_kwh", 0.0)
                    running_usable_area += candidate.get("usable_area_m2", 0.0)
                else:
                    unselected.append(candidate)
            else:
                # No limit -> select all eligible
                selected.append(candidate)
                running_capacity += cand_cap
                running_energy += candidate.get("estimated_annual_energy_kwh", 0.0)
                running_usable_area += candidate.get("usable_area_m2", 0.0)

        # Calculate CO2 offset
        co2_tonnes = (running_energy * GRID_EMISSIONS_FACTOR_KG_KWH) / 1000.0

        utilization_pct = (
            round((running_capacity / max_capacity_kw) * 100.0, 1)
            if max_capacity_kw and max_capacity_kw > 0
            else 100.0
        )

        # Build phased deployment plan
        phase_1_roofs = [s for s in selected if s["surface_type"] == "roof" and s.get("solar_score", 0) >= 0.70]
        phase_2_facades = [s for s in selected if s["surface_type"] == "facade" and s.get("solar_score", 0) >= 0.50]
        phase_3_secondary = [s for s in selected if s not in phase_1_roofs and s not in phase_2_facades]

        phases = []
        if phase_1_roofs:
            p1_cap = sum(s["estimated_capacity_kw"] for s in phase_1_roofs)
            p1_en = sum(s["estimated_annual_energy_kwh"] for s in phase_1_roofs)
            phases.append({
                "phase": 1,
                "name": "Immediate Rooftop Deployment",
                "surface_count": len(phase_1_roofs),
                "capacity_kw": round(p1_cap, 1),
                "annual_energy_kwh": round(p1_en, 1),
                "description": f"Install high-efficiency solar arrays on {len(phase_1_roofs)} top-rated rooftop surfaces.",
            })

        if phase_2_facades:
            p2_cap = sum(s["estimated_capacity_kw"] for s in phase_2_facades)
            p2_en = sum(s["estimated_annual_energy_kwh"] for s in phase_2_facades)
            phases.append({
                "phase": 2,
                "name": "BIPV Facade Integration",
                "surface_count": len(phase_2_facades),
                "capacity_kw": round(p2_cap, 1),
                "annual_energy_kwh": round(p2_en, 1),
                "description": f"Integrate architectural BIPV elements onto {len(phase_2_facades)} optimal south/east/west-facing facades.",
            })

        if phase_3_secondary:
            p3_cap = sum(s["estimated_capacity_kw"] for s in phase_3_secondary)
            p3_en = sum(s["estimated_annual_energy_kwh"] for s in phase_3_secondary)
            phases.append({
                "phase": 3,
                "name": "Supplemental Area Expansion",
                "surface_count": len(phase_3_secondary),
                "capacity_kw": round(p3_cap, 1),
                "annual_energy_kwh": round(p3_en, 1),
                "description": f"Deploy remaining {len(phase_3_secondary)} secondary surfaces to reach target capacity.",
            })

        return {
            "target_capacity_kw": max_capacity_kw,
            "selected_capacity_kw": round(running_capacity, 2),
            "capacity_utilization_pct": utilization_pct,
            "selected_annual_energy_kwh": round(running_energy, 2),
            "selected_usable_area_m2": round(running_usable_area, 2),
            "annual_co2_offset_tonnes": round(co2_tonnes, 2),
            "selected_surfaces_count": len(selected),
            "unselected_surfaces_count": len(unselected),
            "phases": phases,
            "selected_surfaces": selected,
        }


area_optimization_service = AreaOptimizationService()
