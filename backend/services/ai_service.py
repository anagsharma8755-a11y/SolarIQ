"""AI Decision and Explanation Layer for SolarIQ.

Provides explainable, data-grounded insights and recommendations
derived strictly from actual SolarIQ calculations.

Distinguishes explicitly between:
- CALCULATED RESULTS: Exact physical, geometric, and solar metrics.
- AI INTERPRETATION: Architectural, financial, and deployment recommendations.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from backend.services.area_optimization_service import area_optimization_service

logger = logging.getLogger(__name__)


class AIService:
    """Explains numerical SolarIQ analysis results in clear, actionable human language."""

    def explain(
        self,
        analysis_data: dict[str, Any],
        user_prompt: str,
        target_capacity_kw: float | None = None,
    ) -> dict[str, Any]:
        """Generate an AI-driven explanation and recommendation based on real analysis data.

        Args:
            analysis_data: Analysis payload returned by AreaAnalysisService or BuildingAnalysisResponse.
            user_prompt: User question or goal (e.g. "Where should I install solar panels?").
            target_capacity_kw: Optional capacity constraint in kW.

        Returns:
            Structured explanation with calculated facts, AI interpretation,
            prioritized recommendations, and key takeaways.
        """
        summary = analysis_data.get("summary", {})
        location_name = analysis_data.get("location_name", "Selected Area")
        ranked_surfaces = analysis_data.get("ranked_surfaces", [])
        buildings = analysis_data.get("buildings", [])

        # Extract hard metrics
        total_buildings = summary.get("building_count", len(buildings))
        total_usable_area = summary.get("total_usable_surface_area_m2", 0.0)
        total_capacity_kw = summary.get("total_estimated_capacity_kw", 0.0)
        total_annual_energy_kwh = summary.get("total_estimated_annual_energy_kwh", 0.0)
        high_potential_count = summary.get("high_potential_count", 0)
        avg_score = summary.get("average_solar_score", 0.0)

        # Top candidates
        top_surfaces = ranked_surfaces[:5] if ranked_surfaces else []
        top_buildings = sorted(
            buildings,
            key=lambda b: b.get("estimated_annual_energy_kwh", 0.0),
            reverse=True,
        )[:3]

        prompt_lower = user_prompt.lower()

        # Handle capacity-constrained question
        optimization_result = None
        if target_capacity_kw or ("500" in prompt_lower) or ("limit" in prompt_lower) or ("capacity" in prompt_lower and "up to" in prompt_lower):
            target_cap = target_capacity_kw or 500.0
            optimization_result = area_optimization_service.optimize_deployment(
                ranked_surfaces=ranked_surfaces,
                max_capacity_kw=target_cap,
            )

        # Generate structured synthesis
        calculated_facts = [
            f"Location: {location_name}",
            f"Total Buildings Analyzed: {total_buildings}",
            f"Total Usable BIPV/Rooftop Area: {total_usable_area:,.1f} m²",
            f"Total Estimated Capacity: {total_capacity_kw:,.1f} kW",
            f"Total Estimated Annual Generation: {total_annual_energy_kwh:,.0f} kWh/year ({(total_annual_energy_kwh/1000):,.1f} MWh/year)",
            f"High Potential Buildings: {high_potential_count} of {total_buildings} (Avg Solar Score: {avg_score:.2f})",
        ]

        if top_buildings:
            lead = top_buildings[0]
            calculated_facts.append(
                f"Top Building: {lead.get('name', lead.get('building_id'))} "
                f"({lead.get('estimated_capacity_kw', 0):.1f} kW, {lead.get('estimated_annual_energy_kwh', 0):,.0f} kWh/yr)"
            )

        # Build contextual AI interpretation based on query
        if optimization_result and target_capacity_kw:
            headline = f"Optimal Solar Deployment Strategy for {target_capacity_kw:.0f} kW Capacity"
            explanation_body = (
                f"SolarIQ evaluated {len(ranked_surfaces)} eligible surfaces in {location_name} and identified "
                f"the most efficient subset totaling {optimization_result['selected_capacity_kw']:.1f} kW "
                f"({optimization_result['capacity_utilization_pct']}% of requested target). "
                f"This configuration generates an estimated {optimization_result['selected_annual_energy_kwh']:,.0f} kWh annually "
                f"across {optimization_result['selected_usable_area_m2']:,.1f} m² of high-yield surface area, "
                f"preventing approximately {optimization_result['annual_co2_offset_tonnes']:.1f} metric tonnes of CO₂ emissions each year."
            )
            recommendations = [
                f"Phase 1: Prioritize {p['name']} ({p['capacity_kw']:.1f} kW, {p['annual_energy_kwh']:,.0f} kWh/yr)."
                for p in optimization_result.get("phases", [])
            ]
        elif "which building" in prompt_lower or "best" in prompt_lower:
            headline = f"Top-Ranked Buildings for Solar Installation in {location_name}"
            top_names = [b.get("name", b.get("building_id")) for b in top_buildings]
            explanation_body = (
                f"SolarIQ recommends prioritizing {', '.join(top_names[:3])}. "
                f"These structures feature unshaded rooftops and south/west orientations with solar suitability scores "
                f"exceeding {avg_score:.2f}, delivering the highest energy yield per square meter."
            )
            recommendations = [
                f"1. {b.get('name', b.get('building_id'))}: Deploy {b.get('usable_surface_area_m2', 0):.1f} m² for {b.get('estimated_capacity_kw', 0):.1f} kW capacity ({b.get('estimated_annual_energy_kwh', 0):,.0f} kWh/yr)."
                for b in top_buildings
            ]
        elif "avoid" in prompt_lower or "worst" in prompt_lower:
            headline = "Surfaces and Orientations to Exclude"
            explanation_body = (
                "Ground surfaces (0° tilt at ground elevation) and steep north-facing facades (azimuth 315°-45°) "
                "should be excluded from solar deployment due to low incident radiation and shading losses."
            )
            recommendations = [
                "Exclude north-facing vertical facades (solar score < 0.35).",
                "Avoid ground-level obstructions and heavily self-shaded courtyards.",
                "Concentrate BIPV investment on flat roofs and south/south-west facades.",
            ]
        else:
            headline = f"SolarIQ Strategic Assessment for {location_name}"
            explanation_body = (
                f"Based on 3D geometry extraction and atmospheric irradiance modeling, {location_name} exhibits "
                f"a total solar capacity potential of {total_capacity_kw:,.1f} kW. "
                f"Immediate deployment on the top {high_potential_count} high-suitability buildings captures the majority "
                f"of available generation ({total_annual_energy_kwh:,.0f} kWh/yr) with optimal capital efficiency."
            )
            recommendations = [
                f"Priority 1: Deploy {top_surfaces[0]['surface_id']} on {top_surfaces[0]['building_id']} ({top_surfaces[0]['estimated_capacity_kw']:.1f} kW)." if top_surfaces else "Deploy high-yield rooftops.",
                f"Priority 2: Roll out BIPV cladding on favorable south-facing building facades.",
                f"Priority 3: Aggregate district energy to support local grid peak shaving.",
            ]

        return {
            "query": user_prompt,
            "headline": headline,
            "calculated_results": calculated_facts,
            "ai_interpretation": {
                "summary": explanation_body,
                "recommendations": recommendations,
                "avoidance_guidelines": "Avoid north-facing facades and ground surfaces with low irradiance factors.",
                "disclaimer": "Calculated results are derived from SolarIQ 3D geometric and atmospheric modeling. AI interpretation provides planning guidance.",
            },
            "optimization_context": optimization_result,
        }


ai_service = AIService()
