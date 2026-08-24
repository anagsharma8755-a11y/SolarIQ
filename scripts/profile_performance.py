#!/usr/bin/env python3
"""Performance profiling script for SolarIQ backend.

Measures:
- Geometry processing (extract_surfaces)
- Solar analysis (analyze_surface, analyze_building_surfaces)
- Optimization pipeline (optimize_surfaces)
- City analysis at scale

Uses synthetic but realistic building data.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.geometry.surfaces import extract_surfaces
from backend.services.solar_service import analyze_surface
from backend.services.analysis_service import analyze_building_surfaces
from backend.services.optimization_service import optimize_surfaces


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------


def _make_roof_surface(sid: str, w: float = 20.0, h: float = 15.0) -> dict:
    """Create a flat roof surface (4 vertices)."""
    return {
        "surface_id": sid,
        "vertices": [
            [0, 0, h], [w, 0, h], [w, w, h], [0, w, h],
        ],
    }


def _make_facade_surface(sid: str, w: float = 20.0, h: float = 15.0) -> dict:
    """Create a south-facing facade (4 vertices)."""
    return {
        "surface_id": sid,
        "vertices": [
            [0, 0, 0], [w, 0, 0], [w, 0, h], [0, 0, h],
        ],
    }


def _make_ground_surface(sid: str, w: float = 20.0) -> dict:
    """Create a ground surface (4 vertices, facing down)."""
    return {
        "surface_id": sid,
        "vertices": [
            [0, 0, 0], [w, 0, 0], [w, w, 0], [0, w, 0],
        ],
    }


def generate_buildings(
    num_buildings: int,
    surfaces_per_building: int = 10,
) -> list[dict]:
    """Generate synthetic building data at specified scale."""
    buildings = []
    for b in range(num_buildings):
        surfaces = []
        for s in range(surfaces_per_building):
            sid = f"B{b:04d}-S{s:03d}"
            if s % 4 == 0:
                surfaces.append(_make_roof_surface(sid))
            elif s % 4 == 1:
                surfaces.append(_make_facade_surface(sid))
            elif s % 4 == 2:
                surfaces.append(_make_facade_surface(sid))
            else:
                surfaces.append(_make_ground_surface(sid))
        buildings.append({
            "building_id": f"B{b:04d}",
            "name": f"Building {b}",
            "surfaces": surfaces,
        })
    return buildings


# ---------------------------------------------------------------------------
# Benchmarking helpers
# ---------------------------------------------------------------------------


def benchmark(func, iterations: int = 5, **kwargs):
    """Run func(iterations) times and return timing stats."""
    times = []
    result = None
    for _ in range(iterations):
        t0 = time.perf_counter()
        result = func(**kwargs)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return {
        "mean_ms": round(statistics.mean(times) * 1000, 2),
        "median_ms": round(statistics.median(times) * 1000, 2),
        "min_ms": round(min(times) * 1000, 2),
        "max_ms": round(max(times) * 1000, 2),
        "stdev_ms": round(statistics.stdev(times) * 1000, 2) if len(times) > 1 else 0,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Profiling sections
# ---------------------------------------------------------------------------


def profile_geometry(buildings: list[dict], iterations: int = 5):
    """Profile geometry processing (extract_surfaces)."""
    print(f"\n{'='*60}")
    print(f"  GEOMETRY PROCESSING ({len(buildings)} buildings)")
    print(f"{'='*60}")

    stats = benchmark(
        lambda: [extract_surfaces(b) for b in buildings],
        iterations=iterations,
    )
    total_surfaces = sum(len(b["surfaces"]) for b in buildings)
    print(f"  Total surfaces: {total_surfaces}")
    print(f"  Mean: {stats['mean_ms']:.2f} ms")
    print(f"  Median: {stats['median_ms']:.2f} ms")
    print(f"  Min: {stats['min_ms']:.2f} ms")
    print(f"  Max: {stats['max_ms']:.2f} ms")
    print(f"  Per building: {stats['mean_ms']/len(buildings)*1000:.1f} µs")
    return stats


def profile_solar_analysis(buildings: list[dict], iterations: int = 5):
    """Profile solar analysis (analyze_surface)."""
    print(f"\n{'='*60}")
    print(f"  SOLAR ANALYSIS ({len(buildings)} buildings)")
    print(f"{'='*60}")

    # First extract all surfaces
    all_surfaces = []
    for b in buildings:
        all_surfaces.extend(extract_surfaces(b))
    total_surfaces = len(all_surfaces)

    stats = benchmark(
        lambda: [analyze_surface(s) for s in all_surfaces],
        iterations=iterations,
    )
    print(f"  Total surfaces: {total_surfaces}")
    print(f"  Mean: {stats['mean_ms']:.2f} ms")
    print(f"  Median: {stats['median_ms']:.2f} ms")
    print(f"  Per surface: {stats['mean_ms']/total_surfaces*1000:.1f} µs")
    return stats


def profile_building_analysis(buildings: list[dict], iterations: int = 3):
    """Profile full building analysis pipeline."""
    print(f"\n{'='*60}")
    print(f"  BUILDING ANALYSIS PIPELINE ({len(buildings)} buildings)")
    print(f"{'='*60}")

    stats = benchmark(
        lambda: [analyze_building_surfaces(b) for b in buildings],
        iterations=iterations,
    )
    total_surfaces = sum(len(b["surfaces"]) for b in buildings)
    print(f"  Total surfaces: {total_surfaces}")
    print(f"  Mean: {stats['mean_ms']:.2f} ms")
    print(f"  Median: {stats['median_ms']:.2f} ms")
    print(f"  Per building: {stats['mean_ms']/len(buildings)*1000:.1f} µs")
    return stats


def profile_optimization(buildings: list[dict], iterations: int = 3):
    """Profile the optimization pipeline."""
    print(f"\n{'='*60}")
    print(f"  OPTIMIZATION PIPELINE ({len(buildings)} buildings)")
    print(f"{'='*60}")

    stats = benchmark(
        lambda: optimize_surfaces(
            buildings=buildings, limit=20, include_city_summary=True
        ),
        iterations=iterations,
    )
    total_surfaces = sum(len(b["surfaces"]) for b in buildings)
    result = stats["result"]
    print(f"  Total candidates: {result['total_candidates']}")
    print(f"  Filtered: {result['filtered_candidates']}")
    print(f"  Mean: {stats['mean_ms']:.2f} ms")
    print(f"  Median: {stats['median_ms']:.2f} ms")
    return stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 60)
    print("  SolarIQ Performance Profiling")
    print("=" * 60)

    configs = [
        (10, 10),     # 10 buildings, 100 surfaces
        (100, 10),    # 100 buildings, 1000 surfaces
        (100, 50),    # 100 buildings, 5000 surfaces
    ]

    all_results = {}

    for num_bldg, surf_per_bldg in configs:
        total = num_bldg * surf_per_bldg
        print(f"\n\n{'#'*60}")
        print(f"  SCALE: {num_bldg} buildings × {surf_per_bldg} surfaces = {total} surfaces")
        print(f"{'#'*60}")

        buildings = generate_buildings(num_bldg, surf_per_bldg)
        key = f"{num_bldg}b_{total}s"

        all_results[key] = {
            "buildings": num_bldg,
            "total_surfaces": total,
        }

        gs = profile_geometry(buildings)
        all_results[key]["geometry"] = gs["mean_ms"]

        sa = profile_solar_analysis(buildings)
        all_results[key]["solar"] = sa["mean_ms"]

        ba = profile_building_analysis(buildings)
        all_results[key]["building_analysis"] = ba["mean_ms"]

        op = profile_optimization(buildings)
        all_results[key]["optimization"] = op["mean_ms"]

    # Summary
    print(f"\n\n{'='*60}")
    print("  SUMMARY (mean ms)")
    print(f"{'='*60}")
    print(f"  {'Scale':<20} {'Geometry':>10} {'Solar':>10} {'Building':>10} {'Optimize':>10}")
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for key, r in all_results.items():
        print(f"  {key:<20} {r['geometry']:>10.2f} {r['solar']:>10.2f} {r['building_analysis']:>10.2f} {r['optimization']:>10.2f}")

    # Save results
    out_path = PROJECT_ROOT / "docs" / "profile_baseline.json"
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {out_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
