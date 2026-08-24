"""
SolarIQ Backend Demo Script
============================

Loads sample_data/buildings.json, analyzes all buildings,
and prints a summary of solar potential.

Run from the project root:

    python scripts/demo_analysis.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the project root is on the Python path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.geometry.surfaces import extract_surfaces
from backend.services.solar_service import analyze_surface


def load_sample_data() -> dict:
    sample_path = PROJECT_ROOT / "sample_data" / "buildings.json"

    if not sample_path.exists():
        print(f"Error: sample file not found at {sample_path}")
        sys.exit(1)

    with sample_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    data = load_sample_data()
    buildings = data.get("buildings", [])

    print("=" * 60)
    print("  SolarIQ Backend Demo")
    print("=" * 60)
    print(f"\nLoaded {len(buildings)} building(s) from sample data.\n")

    all_surfaces = []

    for building in buildings:
        building_id = building["building_id"]
        name = building.get("name", building_id)

        print(f"--- {name} ({building_id}) ---")

        surfaces = extract_surfaces(building)
        analyzed = [analyze_surface(s) for s in surfaces]

        total_area = sum(s["area_m2"] for s in analyzed)
        usable_area = sum(
            s["energy_potential"]["usable_area_m2"]
            for s in analyzed
            if s["surface_type"] != "ground"
        )
        capacity = sum(
            s["energy_potential"]["estimated_capacity_kw"]
            for s in analyzed
            if s["surface_type"] != "ground"
        )
        energy = sum(
            s["energy_potential"]["estimated_annual_energy_kwh"]
            for s in analyzed
            if s["surface_type"] != "ground"
        )

        print(f"  Surfaces: {len(analyzed)}")
        print(f"  Total area: {total_area:.1f} m²")
        print(f"  Usable area: {usable_area:.1f} m²")
        print(f"  Estimated capacity: {capacity:.2f} kW")
        print(f"  Annual energy: {energy:.1f} kWh")

        for s in analyzed:
            print(
                f"    - {s['surface_id']}: "
                f"{s['surface_type']}, "
                f"{s['area_m2']:.1f} m², "
                f"score={s['solar_score']:.2f}, "
                f"suitability={s['solar_suitability']}"
            )

        print()
        all_surfaces.extend(analyzed)

    # Best solar surfaces
    ranked = sorted(
        [
            s for s in all_surfaces
            if s["surface_type"] != "ground"
        ],
        key=lambda s: s["solar_score"],
        reverse=True,
    )

    print("=" * 60)
    print("  Best Solar Surfaces")
    print("=" * 60)

    for i, s in enumerate(ranked[:5], start=1):
        print(
            f"  #{i}  {s['building_id']}/{s['surface_id']}  "
            f"score={s['solar_score']:.2f}  "
            f"{s['energy_potential']['estimated_capacity_kw']:.2f} kW"
        )

    # Totals
    total_capacity = sum(
        s["energy_potential"]["estimated_capacity_kw"]
        for s in all_surfaces
        if s["surface_type"] != "ground"
    )
    total_energy = sum(
        s["energy_potential"]["estimated_annual_energy_kwh"]
        for s in all_surfaces
        if s["surface_type"] != "ground"
    )

    print()
    print("=" * 60)
    print("  Totals")
    print("=" * 60)
    print(f"  Total estimated capacity: {total_capacity:.2f} kW")
    print(f"  Total annual energy: {total_energy:.1f} kWh")
    print()
    print("Demo complete.")


if __name__ == "__main__":
    main()
