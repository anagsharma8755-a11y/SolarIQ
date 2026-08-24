"""Area analysis service orchestrating the complete real-world SolarIQ pipeline.

Pipeline flow:
1. Coordinates / Location Search
2. GIS Data Retrieval (OSM / Overpass or bundled dataset)
3. Weather and Solar Irradiance Retrieval (Open-Meteo / Regional)
4. Coordinate Transformation & LOD-1 Geometry Extrusion (UTM metric)
5. Surface Extraction (Roof, Facades, Ground)
6. Solar Suitability Scoring & Usable Area Calculation
7. Energy & PV Capacity Estimation
8. ML Integration (if model available)
9. Multi-factor Surface and Building Ranking
10. GeoJSON Map Overlay Generation & Area Summary Metrics
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from backend.geometry.surfaces import extract_surfaces
from backend.services.analysis_service import analyze_building_surfaces
from backend.services.geocoding_service import geocoding_service
from backend.services.gis_service import gis_service
from backend.services.ml_service import ml_service
from backend.services.optimization_service import optimize_surfaces, get_default_weights
from backend.services.solar_service import (
    analyze_surface,
    calculate_installation_priority,
    calculate_solar_score,
    estimate_energy_potential,
    suitability_label,
)
from backend.services.weather_solar_service import weather_solar_service

logger = logging.getLogger(__name__)

# In-memory store for recent area analyses
_ANALYSIS_STORE: dict[str, dict[str, Any]] = {}


class AreaAnalysisService:
    """End-to-end service for analyzing real-world urban areas."""

    def analyze_area(
        self,
        latitude: float,
        longitude: float,
        radius_m: float = 400.0,
        location_name: str | None = None,
        max_buildings: int = 50,
    ) -> dict[str, Any]:
        """Perform comprehensive solar and BIPV analysis for a geographic area.

        Args:
            latitude: Center latitude (WGS84).
            longitude: Center longitude (WGS84).
            radius_m: Analysis radius in meters (100 - 2000m).
            location_name: Optional label for the area.
            max_buildings: Maximum buildings to analyze.

        Returns:
            Dictionary containing analysis_id, area summary, analyzed buildings,
            ranked surfaces, map GeoJSON, and weather context.
        """
        analysis_id = str(uuid.uuid4())
        radius_m = max(50.0, min(3000.0, float(radius_m)))

        # 1. Fetch weather & solar irradiance for the area
        weather_info = weather_solar_service.get_area_weather_and_solar(latitude, longitude)
        annual_irradiance = weather_info.get("annual_irradiance_kwh_m2", 1700.0)

        # 2. Fetch building footprints from OSM/Overpass (or fallback)
        raw_buildings, is_live_gis = gis_service.fetch_buildings_for_area(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            max_buildings=max_buildings,
        )

        analyzed_buildings: list[dict[str, Any]] = []
        map_features: list[dict[str, Any]] = []
        all_candidate_surfaces: list[dict[str, Any]] = []

        total_analyzed_surfaces = 0
        total_surface_area_m2 = 0.0
        total_usable_area_m2 = 0.0
        total_capacity_kw = 0.0
        total_annual_energy_kwh = 0.0

        high_count = 0
        medium_count = 0
        low_count = 0

        # Process each building through the SolarIQ geometry and solar engines
        for b_raw in raw_buildings:
            try:
                # Convert footprint to SolarIQ LOD-1 internal structure
                solariq_bld = gis_service.convert_to_solariq_geometry(
                    b_raw,
                    origin_lat=latitude,
                    origin_lon=longitude,
                )

                # Extract surfaces and analyze each surface
                surfaces = extract_surfaces(solariq_bld)
                analyzed_surfaces: list[dict[str, Any]] = []

                b_usable_area = 0.0
                b_capacity = 0.0
                b_energy = 0.0
                b_total_area = 0.0
                b_max_score = 0.0
                best_surface_id: str | None = None
                best_surface_type: str = "roof"

                for s in surfaces:
                    # Analyze surface geometry and solar suitability
                    analyzed_s = analyze_surface(s)
                    if analyzed_s["surface_type"] != "ground":
                        # Recalculate energy potential using area-specific annual irradiance
                        energy_pot = estimate_energy_potential(
                            analyzed_s,
                            annual_irradiance_kwh_m2=annual_irradiance,
                        )
                        analyzed_s["energy_potential"] = energy_pot
                    else:
                        energy_pot = analyzed_s["energy_potential"]

                    # Run ML prediction if connected
                    ml_pred = ml_service.predict_if_available(analyzed_s)
                    analyzed_s["ml_prediction"] = ml_pred

                    analyzed_surfaces.append(analyzed_s)
                    b_total_area += analyzed_s["area_m2"]

                    if analyzed_s["surface_type"] != "ground":
                        u_area = energy_pot["usable_area_m2"]
                        cap = energy_pot["estimated_capacity_kw"]
                        en = energy_pot["estimated_annual_energy_kwh"]
                        score = analyzed_s["solar_score"]

                        b_usable_area += u_area
                        b_capacity += cap
                        b_energy += en

                        if score > b_max_score:
                            b_max_score = score
                            best_surface_id = analyzed_s["surface_id"]
                            best_surface_type = analyzed_s["surface_type"]

                        # Add non-ground surfaces to optimization candidate pool
                        all_candidate_surfaces.append({
                            "building_id": solariq_bld["building_id"],
                            "building_name": solariq_bld["name"],
                            "surface_id": analyzed_s["surface_id"],
                            "surface_type": analyzed_s["surface_type"],
                            "area_m2": analyzed_s["area_m2"],
                            "azimuth_deg": analyzed_s["azimuth_deg"],
                            "tilt_deg": analyzed_s["tilt_deg"],
                            "solar_score": score,
                            "solar_suitability": analyzed_s["solar_suitability"],
                            "usable_area_m2": u_area,
                            "estimated_capacity_kw": cap,
                            "estimated_annual_energy_kwh": en,
                        })

                # Determine building overall suitability label
                b_suitability = suitability_label(b_max_score)
                if b_max_score >= 0.70:
                    high_count += 1
                elif b_max_score >= 0.45:
                    medium_count += 1
                else:
                    low_count += 1

                bld_response = {
                    "building_id": solariq_bld["building_id"],
                    "name": solariq_bld["name"],
                    "building_type": b_raw.get("building_type", "yes"),
                    "height_m": solariq_bld["height_m"],
                    "height_estimated": solariq_bld["height_estimated"],
                    "levels": solariq_bld["levels"],
                    "coordinates": solariq_bld["coordinates"],
                    "polygon_wgs84": b_raw.get("polygon_wgs84", []),
                    "surface_count": len(analyzed_surfaces),
                    "total_surface_area_m2": round(b_total_area, 2),
                    "usable_surface_area_m2": round(b_usable_area, 2),
                    "estimated_capacity_kw": round(b_capacity, 2),
                    "estimated_annual_energy_kwh": round(b_energy, 2),
                    "max_solar_score": round(b_max_score, 4),
                    "solar_suitability": b_suitability,
                    "best_surface_id": best_surface_id,
                    "best_surface_type": best_surface_type,
                    "surfaces": analyzed_surfaces,
                }

                analyzed_buildings.append(bld_response)

                total_analyzed_surfaces += len(analyzed_surfaces)
                total_surface_area_m2 += b_total_area
                total_usable_area_m2 += b_usable_area
                total_capacity_kw += b_capacity
                total_annual_energy_kwh += b_energy

                # Create GeoJSON map feature for frontend visualization
                map_features.append({
                    "type": "Feature",
                    "id": solariq_bld["building_id"],
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [b_raw.get("polygon_wgs84", [])],
                    },
                    "properties": {
                        "building_id": solariq_bld["building_id"],
                        "name": solariq_bld["name"],
                        "height_m": solariq_bld["height_m"],
                        "height_estimated": solariq_bld["height_estimated"],
                        "solar_score": round(b_max_score, 3),
                        "solar_suitability": b_suitability,
                        "usable_area_m2": round(b_usable_area, 1),
                        "estimated_capacity_kw": round(b_capacity, 1),
                        "estimated_annual_energy_kwh": round(b_energy, 1),
                        "best_surface": f"{best_surface_type.title()} ({b_max_score:.2f})",
                        "color": (
                            "#10b981" if b_max_score >= 0.70  # Green/High
                            else "#f59e0b" if b_max_score >= 0.45  # Amber/Medium
                            else "#64748b"  # Slate/Low
                        ),
                    },
                })

            except Exception as exc:
                logger.warning("Failed to process building %s: %s", b_raw.get("building_id"), exc)

        # Multi-factor ranking of surfaces across the entire area
        ranked_surfaces = self._rank_area_surfaces(all_candidate_surfaces)

        # Identify top-performing assets
        top_building = max(analyzed_buildings, key=lambda b: b["estimated_annual_energy_kwh"]) if analyzed_buildings else None
        avg_solar_score = (
            sum(b["max_solar_score"] for b in analyzed_buildings) / len(analyzed_buildings)
            if analyzed_buildings else 0.0
        )

        area_summary = {
            "building_count": len(analyzed_buildings),
            "surface_count": total_analyzed_surfaces,
            "total_surface_area_m2": round(total_surface_area_m2, 1),
            "total_usable_surface_area_m2": round(total_usable_area_m2, 1),
            "total_estimated_capacity_kw": round(total_capacity_kw, 1),
            "total_estimated_annual_energy_kwh": round(total_annual_energy_kwh, 1),
            "high_potential_count": high_count,
            "medium_potential_count": medium_count,
            "low_potential_count": low_count,
            "average_solar_score": round(avg_solar_score, 3),
            "top_performing_building": top_building["building_id"] if top_building else None,
            "top_building_name": top_building["name"] if top_building else None,
            "capacity_density_kw_per_m2": (
                round(total_capacity_kw / max(1.0, total_usable_area_m2), 4)
                if total_usable_area_m2 > 0 else 0.0
            ),
        }

        geojson_map = {
            "type": "FeatureCollection",
            "features": map_features,
        }

        resolved_name = location_name or f"Area ({latitude:.4f}, {longitude:.4f})"

        data_source_label = "LIVE OSM + Open-Meteo" if (is_live_gis and weather_info["is_real_data"]) else (
            "LIVE OSM + Regional Weather" if is_live_gis else "OFFLINE DEMO DATA"
        )

        result = {
            "analysis_id": analysis_id,
            "location_name": resolved_name,
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_m,
            "data_provenance": {
                "source": data_source_label,
                "is_live_data": is_live_gis,
                "weather": weather_info,
            },
            "summary": area_summary,
            "buildings": analyzed_buildings,
            "ranked_surfaces": ranked_surfaces,
            "geojson": geojson_map,
        }

        # Store in analysis cache
        _ANALYSIS_STORE[analysis_id] = result

        return result

    def _rank_area_surfaces(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rank all building surfaces across the area using multi-factor weighted scoring."""
        if not candidates:
            return []

        max_energy = max((c["estimated_annual_energy_kwh"] for c in candidates), default=1.0)
        max_capacity = max((c["estimated_capacity_kw"] for c in candidates), default=1.0)
        max_area = max((c["usable_area_m2"] for c in candidates), default=1.0)

        weights = get_default_weights()
        scored: list[dict[str, Any]] = []

        for c in candidates:
            suit_norm = c["solar_score"]
            en_norm = c["estimated_annual_energy_kwh"] / max(1.0, max_energy)
            cap_norm = c["estimated_capacity_kw"] / max(1.0, max_capacity)
            area_norm = c["usable_area_m2"] / max(1.0, max_area)

            # Orientation factor
            az = c["azimuth_deg"]
            dev = abs((az % 360) - 180.0)
            if dev > 180.0:
                dev = 360.0 - dev
            ori_norm = 1.0 - (dev / 180.0)

            composite = (
                weights["suitability"] * suit_norm
                + weights["energy"] * en_norm
                + weights["capacity"] * cap_norm
                + weights["area"] * area_norm
                + weights["orientation"] * ori_norm
            )

            # Generate recommendation rationale
            if composite >= 0.70:
                rec = f"Priority 1: High yield {c['surface_type']} ({c['estimated_capacity_kw']:.1f} kW, {c['estimated_annual_energy_kwh']:,.0f} kWh/yr)"
            elif composite >= 0.45:
                rec = f"Priority 2: Moderate yield {c['surface_type']} with good usable area"
            else:
                rec = f"Priority 3: Secondary candidate for supplemental capacity"

            scored.append({
                **c,
                "composite_score": round(composite, 4),
                "recommendation": rec,
            })

        # Sort descending by composite score
        scored.sort(key=lambda s: s["composite_score"], reverse=True)

        # Assign ranks
        for idx, s in enumerate(scored, start=1):
            s["rank"] = idx

        return scored

    def get_analysis_by_id(self, analysis_id: str) -> dict[str, Any] | None:
        """Retrieve a stored area analysis by its unique ID."""
        return _ANALYSIS_STORE.get(analysis_id)


area_analysis_service = AreaAnalysisService()
