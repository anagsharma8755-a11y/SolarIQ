"""Comprehensive tests for the enhanced geometry engine.

Covers:
- Reversed vertex winding detection and correction
- Degenerate polygon handling
- Triangles, irregular polygons, arbitrary planar polygons
- Centroid and bounding box
- Planarity checking
- Geospatial projections and CRS metadata
- LOD-2 architecture and validation
- Shading/obstruction interface
- Existing LOD-1 regression (backward compatibility)
"""

import math

import pytest

from backend.geometry.calculations import (
    calculate_azimuth,
    calculate_bounding_box,
    calculate_centroid,
    calculate_normal,
    calculate_polygon_area,
    calculate_polygon_area_signed,
    calculate_tilt,
    classify_surface,
    is_degenerate_polygon,
    is_planar,
    is_reversed_winding,
    normalise_winding,
)
from backend.geometry.surfaces import extract_surfaces


# =====================================================================
# Reversed winding
# =====================================================================


class TestReversedWinding:
    """Tests for reversed (clockwise) vertex winding."""

    def test_ccw_roof_has_upward_normal(self):
        """CCW winding on a horizontal roof -> upward normal."""
        vertices = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
            [0, 20, 10],
        ]
        normal = calculate_normal(vertices)
        assert normal[2] > 0  # Points upward

    def test_cw_roof_has_downward_normal(self):
        """CW winding on a horizontal roof -> downward normal."""
        vertices = [
            [0, 0, 10],
            [0, 20, 10],
            [20, 20, 10],
            [20, 0, 10],
        ]
        normal = calculate_normal(vertices)
        assert normal[2] < 0  # Points downward

    def test_reversed_winding_detection(self):
        """Detect reversed winding."""
        ccw = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
        ]
        cw = [
            [0, 0, 10],
            [20, 20, 10],
            [20, 0, 10],
        ]
        assert not is_reversed_winding(ccw)
        assert is_reversed_winding(cw)

    def test_signed_area_positive_for_ccw(self):
        """CCW polygon has positive signed area."""
        vertices = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
            [0, 20, 10],
        ]
        assert calculate_polygon_area_signed(vertices) > 0

    def test_signed_area_negative_for_cw(self):
        """CW polygon has negative signed area."""
        vertices = [
            [0, 0, 10],
            [0, 20, 10],
            [20, 20, 10],
            [20, 0, 10],
        ]
        assert calculate_polygon_area_signed(vertices) < 0

    def test_normalise_winding_fixes_cw_roof(self):
        """normalise_winding corrects CW roof to CCW."""
        cw_roof = [
            [0, 0, 10],
            [0, 20, 10],
            [20, 20, 10],
            [20, 0, 10],
        ]
        fixed = normalise_winding(cw_roof)
        normal = calculate_normal(fixed)
        assert normal[2] > 0  # Now points upward

    def test_normalise_winding_preserves_ccw(self):
        """normalise_winding leaves CCW polygons unchanged."""
        ccw = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
            [0, 20, 10],
        ]
        fixed = normalise_winding(ccw)
        normal = calculate_normal(fixed)
        assert normal[2] > 0

    def test_extract_surfaces_corrects_reversed_winding(self):
        """extract_surfaces auto-corrects CW winding."""
        building = {
            "building_id": "B-REV",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 10],
                        [0, 20, 10],
                        [20, 20, 10],
                        [20, 0, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        assert len(surfaces) == 1
        s = surfaces[0]
        assert s["surface_type"] == "roof"
        assert s["reversed_winding_corrected"] == True
        assert s["area_m2"] == pytest.approx(400.0)

    def test_vertical_facade_reversed_winding(self):
        """Reversed winding on a vertical facade."""
        # Normal CW vertical surface.
        cw = [
            [0, 0, 0],
            [0, 20, 0],
            [0, 20, 10],
            [0, 0, 10],
        ]
        # After normalisation the surface should still be a facade.
        fixed = normalise_winding(cw)
        normal = calculate_normal(fixed)
        assert classify_surface(normal) == "facade"


# =====================================================================
# Degenerate polygons
# =====================================================================


class TestDegeneratePolygons:
    """Tests for degenerate polygon detection."""

    def test_two_vertices_is_degenerate(self):
        verts = [[0, 0, 0], [1, 0, 0]]
        assert is_degenerate_polygon(verts)

    def test_collinear_vertices_is_degenerate(self):
        verts = [[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]]
        assert is_degenerate_polygon(verts)

    def test_zero_area_polygon_is_degenerate(self):
        # All points at the same location.
        verts = [[5, 5, 5], [5, 5, 5], [5, 5, 5]]
        assert is_degenerate_polygon(verts)

    def test_valid_triangle_not_degenerate(self):
        verts = [[0, 0, 0], [10, 0, 0], [5, 10, 0]]
        assert not is_degenerate_polygon(verts)

    def test_valid_quad_not_degenerate(self):
        verts = [[0, 0, 10], [20, 0, 10], [20, 20, 10], [0, 20, 10]]
        assert not is_degenerate_polygon(verts)

    def test_extract_surfaces_rejects_degenerate(self):
        building = {
            "building_id": "B-DEG",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 0],
                        [1, 0, 0],
                        [2, 0, 0],
                    ],
                }
            ],
        }
        with pytest.raises(ValueError, match="degenerate"):
            extract_surfaces(building)

    def test_empty_list_is_degenerate(self):
        assert is_degenerate_polygon([])

    def test_single_vertex_is_degenerate(self):
        assert is_degenerate_polygon([[0, 0, 0]])


# =====================================================================
# Triangles and irregular polygons
# =====================================================================


class TestTrianglesAndIrregularPolygons:
    """Tests for non-quad polygon types."""

    def test_triangle_area(self):
        """Right triangle area = 0.5 * base * height."""
        verts = [[0, 0, 0], [10, 0, 0], [0, 10, 0]]
        area = calculate_polygon_area(verts)
        assert area == pytest.approx(50.0)

    def test_triangle_normal(self):
        """Triangle in XY plane -> normal along Z."""
        verts = [[0, 0, 5], [10, 0, 5], [5, 10, 5]]
        normal = calculate_normal(verts)
        assert normal[2] == pytest.approx(1.0)

    def test_irregular_polygon_area(self):
        """L-shaped polygon (concave)."""
        verts = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 10, 10],
            [10, 10, 10],
            [10, 20, 10],
            [0, 20, 10],
        ]
        area = calculate_polygon_area(verts)
        # L-shape = 20*10 + 10*10 = 300
        assert area == pytest.approx(300.0)

    def test_irregular_polygon_is_not_degenerate(self):
        verts = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 10, 10],
            [10, 10, 10],
            [10, 20, 10],
            [0, 20, 10],
        ]
        assert not is_degenerate_polygon(verts)

    def test_pentagon_area(self):
        """Regular pentagon approximation."""
        n = 5
        r = 10.0
        verts = [
            [r * math.cos(2 * math.pi * i / n),
             r * math.sin(2 * math.pi * i / n),
             5.0]
            for i in range(n)
        ]
        area = calculate_polygon_area(verts)
        # Area of regular pentagon with circumradius 10
        expected = 0.5 * n * r * r * math.sin(2 * math.pi / n)
        assert area == pytest.approx(expected, rel=0.01)

    def test_extract_surfaces_triangle(self):
        """extract_surfaces handles triangular surfaces."""
        building = {
            "building_id": "B-TRI",
            "surfaces": [
                {
                    "surface_id": "TRI-1",
                    "vertices": [
                        [0, 0, 10],
                        [10, 0, 10],
                        [5, 10, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        assert len(surfaces) == 1
        assert surfaces[0]["surface_type"] == "roof"
        assert surfaces[0]["area_m2"] == pytest.approx(50.0)

    def test_extract_surfaces_irregular(self):
        """extract_surfaces handles L-shaped polygon."""
        building = {
            "building_id": "B-L",
            "surfaces": [
                {
                    "surface_id": "L-1",
                    "vertices": [
                        [0, 0, 10],
                        [20, 0, 10],
                        [20, 10, 10],
                        [10, 10, 10],
                        [10, 20, 10],
                        [0, 20, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        assert surfaces[0]["area_m2"] == pytest.approx(300.0)


# =====================================================================
# Centroid and bounding box
# =====================================================================


class TestCentroid:
    """Tests for centroid computation."""

    def test_centroid_square(self):
        verts = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
            [0, 20, 10],
        ]
        c = calculate_centroid(verts)
        assert c == pytest.approx([10.0, 10.0, 10.0])

    def test_centroid_triangle(self):
        verts = [[0, 0, 0], [6, 0, 0], [3, 9, 0]]
        c = calculate_centroid(verts)
        assert c == pytest.approx([3.0, 3.0, 0.0])

    def test_centroid_single_point(self):
        c = calculate_centroid([[5, 5, 5]])
        assert c == pytest.approx([5.0, 5.0, 5.0])

    def test_centroid_raises_on_empty(self):
        with pytest.raises(ValueError):
            calculate_centroid([])


class TestBoundingBox:
    """Tests for axis-aligned bounding box."""

    def test_bbox_square(self):
        verts = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
            [0, 20, 10],
        ]
        bb = calculate_bounding_box(verts)
        assert bb["min_x"] == 0.0
        assert bb["max_x"] == 20.0
        assert bb["min_y"] == 0.0
        assert bb["max_y"] == 20.0
        assert bb["min_z"] == 10.0
        assert bb["max_z"] == 10.0
        assert bb["width_x"] == 20.0
        assert bb["width_y"] == 20.0
        assert bb["height_z"] == 0.0

    def test_bbox_3d(self):
        verts = [[-1, 2, 3], [5, -4, 7], [0, 0, 0]]
        bb = calculate_bounding_box(verts)
        assert bb["min_x"] == -1.0
        assert bb["max_x"] == 5.0
        assert bb["min_y"] == -4.0
        assert bb["max_y"] == 2.0
        assert bb["min_z"] == 0.0
        assert bb["max_z"] == 7.0

    def test_bbox_raises_on_empty(self):
        with pytest.raises(ValueError):
            calculate_bounding_box([])


class TestSurfaceMetadata:
    """Tests that extract_surfaces includes new metadata fields."""

    def test_centroid_in_output(self):
        building = {
            "building_id": "B-META",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 10],
                        [20, 0, 10],
                        [20, 20, 10],
                        [0, 20, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        s = surfaces[0]
        assert "centroid" in s
        assert s["centroid"] == pytest.approx([10.0, 10.0, 10.0])

    def test_bounding_box_in_output(self):
        building = {
            "building_id": "B-BBOX",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 10],
                        [20, 0, 10],
                        [20, 20, 10],
                        [0, 20, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        bb = surfaces[0]["bounding_box"]
        assert bb["width_x"] == 20.0
        assert bb["width_y"] == 20.0

    def test_reversed_winding_flag(self):
        building = {
            "building_id": "B-FLAG",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 10],
                        [0, 20, 10],
                        [20, 20, 10],
                        [20, 0, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        assert surfaces[0]["reversed_winding_corrected"] == True

    def test_no_reversed_flag_when_ccw(self):
        building = {
            "building_id": "B-NOFLAG",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 10],
                        [20, 0, 10],
                        [20, 20, 10],
                        [0, 20, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        assert surfaces[0]["reversed_winding_corrected"] == False


# =====================================================================
# Planarity check
# =====================================================================


class TestPlanarity:
    """Tests for the is_planar function."""

    def test_flat_surface_is_planar(self):
        verts = [
            [0, 0, 10],
            [20, 0, 10],
            [20, 20, 10],
            [0, 20, 10],
        ]
        assert is_planar(verts)

    def test_tilted_surface_is_planar(self):
        verts = [
            [0, 0, 0],
            [10, 0, 0],
            [10, 0, 10],
            [0, 0, 10],
        ]
        assert is_planar(verts)

    def test_non_planar_is_detected(self):
        """Pyramid-like shape: 4 base points + peak."""
        verts = [
            [0, 0, 0],
            [10, 0, 0],
            [10, 10, 0],
            [0, 10, 0],
            [5, 5, 10],  # Peak above the base
        ]
        assert not is_planar(verts)

    def test_triangle_is_always_planar(self):
        assert is_planar([[0, 0, 0], [1, 0, 0], [0, 1, 0]])

    def test_two_points_is_planar(self):
        assert is_planar([[0, 0, 0], [1, 1, 1]])


# =====================================================================
# Geospatial projections
# =====================================================================


class TestProjections:
    """Tests for geospatial projection helpers."""

    def test_utm_zone_mumbai(self):
        from backend.geometry.projections import get_utm_zone
        # Mumbai longitude ~72.88 -> zone 43
        assert get_utm_zone(72.8777) == 43

    def test_utm_zone_new_york(self):
        from backend.geometry.projections import get_utm_zone
        assert get_utm_zone(-73.9857) == 18

    def test_utm_epsg_northern(self):
        from backend.geometry.projections import get_utm_epsg
        # Mumbai: lat 19.07, lon 72.88 -> EPSG 32643
        assert get_utm_epsg(19.07, 72.88) == 32643

    def test_utm_epsg_southern(self):
        from backend.geometry.projections import get_utm_epsg
        # Sydney: lat -33.87, lon 151.21 -> zone 56, S -> 32756
        assert get_utm_epsg(-33.87, 151.21) == 32756

    def test_vertices_to_utm_and_back(self):
        from backend.geometry.projections import (
            vertices_to_utm,
            vertices_to_wgs84,
        )
        lat, lon = 19.076, 72.878  # Mumbai
        verts = [
            [lon, lat, 10.0],
            [lon + 0.001, lat, 10.0],
            [lon + 0.001, lat + 0.001, 10.0],
            [lon, lat + 0.001, 10.0],
        ]
        utm = vertices_to_utm(verts, lat, lon)
        # UTM coordinates should be in metres.
        for v in utm:
            assert v[0] > 100000  # Mumbai easting (UTM zone 43)
            assert v[1] > 2000000  # Mumbai northing

        # Round-trip back to WGS84.
        back = vertices_to_wgs84(utm, lat, lon)
        for orig, rec in zip(verts, back):
            assert orig[0] == pytest.approx(rec[0], abs=1e-5)
            assert orig[1] == pytest.approx(rec[1], abs=1e-5)

    def test_crs_metadata(self):
        from backend.geometry.projections import make_crs_metadata
        meta = make_crs_metadata(19.076, 72.878)
        assert meta["utm_zone"] == 43
        assert meta["hemisphere"] == "N"
        assert meta["projected_crs"] == "EPSG:32643"

    def test_crs_metadata_without_coords(self):
        from backend.geometry.projections import make_crs_metadata
        meta = make_crs_metadata()
        assert meta["utm_zone"] is None
        assert meta["projected_crs"] is None

    def test_area_in_m2_geographic(self):
        from backend.geometry.projections import calculate_area_in_m2
        lat, lon = 19.076, 72.878
        # ~0.001 degree square at this latitude.
        verts = [
            [lon, lat, 0.0],
            [lon + 0.001, lat, 0.0],
            [lon + 0.001, lat + 0.001, 0.0],
            [lon, lat + 0.001, 0.0],
        ]
        area = calculate_area_in_m2(verts, lat, lon)
        # Should be roughly 100m x 110m ~ 11000 m^2.
        assert area > 5000
        assert area < 20000

    def test_area_in_m2_projected(self):
        from backend.geometry.projections import calculate_area_in_m2
        # Already in metres (UTM-like).
        verts = [
            [0, 0, 10],
            [100, 0, 10],
            [100, 50, 10],
            [0, 50, 10],
        ]
        area = calculate_area_in_m2(verts)
        assert area == pytest.approx(5000.0)


# =====================================================================
# LOD-2 architecture
# =====================================================================


class TestLOD2:
    """Tests for LOD-2 building representation."""

    def test_gable_building_creation(self):
        from backend.geometry.lod2 import (
            create_sample_gable_building,
            RoofType,
        )
        bld = create_sample_gable_building()
        assert bld.building_id == "LOD2-001"
        assert bld.roof_type == RoofType.GABLE
        assert len(bld.roof_planes) == 2
        assert len(bld.ridges) == 1

    def test_hip_building_creation(self):
        from backend.geometry.lod2 import (
            create_sample_multiplane_building,
            RoofType,
        )
        bld = create_sample_multiplane_building()
        assert bld.roof_type == RoofType.HIP
        assert len(bld.roof_planes) == 4

    def test_validate_gable_building(self):
        from backend.geometry.lod2 import (
            create_sample_gable_building,
            validate_lod2_building,
        )
        bld = create_sample_gable_building()
        errors = validate_lod2_building(bld)
        assert errors == []

    def test_validate_rejects_missing_id(self):
        from backend.geometry.lod2 import (
            LOD2Building,
            LODLevel,
            validate_lod2_building,
        )
        bld = LOD2Building(building_id="", lod=LODLevel.LOD2)
        errors = validate_lod2_building(bld)
        assert any("building_id" in e for e in errors)

    def test_validate_rejects_wrong_lod(self):
        from backend.geometry.lod2 import (
            LOD2Building,
            LODLevel,
            validate_lod2_building,
        )
        bld = LOD2Building(building_id="X", lod=LODLevel.LOD1)
        errors = validate_lod2_building(bld)
        assert any("LOD" in e for e in errors)

    def test_validate_rejects_degenerate_plane(self):
        from backend.geometry.lod2 import (
            LOD2Building,
            LODLevel,
            RoofPlane,
            validate_lod2_building,
        )
        plane = RoofPlane(
            plane_id="BAD",
            vertices=[[0, 0, 0], [1, 0, 0], [2, 0, 0]],
        )
        bld = LOD2Building(
            building_id="X",
            lod=LODLevel.LOD2,
            roof_planes=[plane],
        )
        errors = validate_lod2_building(bld)
        assert any("degenerate" in e for e in errors)

    def test_lod2_to_lod1_conversion(self):
        from backend.geometry.lod2 import (
            create_sample_gable_building,
            lod2_to_lod1_surfaces,
        )
        bld = create_sample_gable_building()
        surfaces = lod2_to_lod1_surfaces(bld)
        assert len(surfaces) == 2
        assert all(s["lod"] == 2 for s in surfaces)
        assert all(s["building_id"] == "LOD2-001" for s in surfaces)

    def test_lod2_plane_areas_are_positive(self):
        from backend.geometry.lod2 import (
            create_sample_gable_building,
            validate_roof_plane,
        )
        bld = create_sample_gable_building()
        for plane in bld.roof_planes:
            errors = validate_roof_plane(plane)
            assert errors == [], f"Plane {plane.plane_id}: {errors}"


# =====================================================================
# Shading / obstruction interface
# =====================================================================


class TestShading:
    """Tests for the shading analysis interface."""

    def test_no_sources_returns_no_shading(self):
        from backend.geometry.shading import ShadingAnalyzer
        analyzer = ShadingAnalyzer()
        result = analyzer.analyze_surface(
            "S001",
            [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
        )
        assert result.has_shading is False

    def test_nearby_tall_building_causes_shading(self):
        from backend.geometry.shading import (
            ShadingAnalyzer,
            ShadingSource,
            ShadingType,
        )
        analyzer = ShadingAnalyzer()
        source = ShadingSource(
            source_id="B002",
            shading_type=ShadingType.BUILDING,
            height_m=20.0,
            distance_m=30.0,
        )
        result = analyzer.analyze_surface(
            "S001",
            [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
            [source],
        )
        assert result.has_shading is True
        assert len(result.sources) == 1

    def test_distant_building_no_shading(self):
        from backend.geometry.shading import (
            ShadingAnalyzer,
            ShadingSource,
            ShadingType,
        )
        analyzer = ShadingAnalyzer(max_shading_distance_m=50.0)
        source = ShadingSource(
            source_id="B-FAR",
            shading_type=ShadingType.BUILDING,
            height_m=20.0,
            distance_m=200.0,  # Too far.
        )
        result = analyzer.analyze_surface(
            "S001",
            [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
            [source],
        )
        assert result.has_shading is False

    def test_short_source_no_shading(self):
        from backend.geometry.shading import (
            ShadingAnalyzer,
            ShadingSource,
            ShadingType,
        )
        analyzer = ShadingAnalyzer(min_height_threshold_m=5.0)
        source = ShadingSource(
            source_id="B-SHORT",
            shading_type=ShadingType.BUILDING,
            height_m=2.0,  # Below threshold.
            distance_m=10.0,
        )
        result = analyzer.analyze_surface(
            "S001",
            [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
            [source],
        )
        assert result.has_shading is False

    def test_shading_fraction_range(self):
        from backend.geometry.shading import (
            ShadingAnalyzer,
            ShadingSource,
            ShadingType,
        )
        analyzer = ShadingAnalyzer()
        source = ShadingSource(
            source_id="B002",
            shading_type=ShadingType.BUILDING,
            height_m=30.0,
            distance_m=10.0,
        )
        result = analyzer.analyze_surface(
            "S001",
            [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
            [source],
        )
        assert 0.0 <= result.estimated_shading_fraction <= 1.0

    def test_analyze_building(self):
        from backend.geometry.shading import (
            ShadingAnalyzer,
            ShadingSource,
            ShadingType,
        )
        analyzer = ShadingAnalyzer()
        surfaces = [
            {
                "surface_id": "S001",
                "vertices": [[0, 0, 10], [10, 0, 10], [10, 10, 10], [0, 10, 10]],
            },
            {
                "surface_id": "S002",
                "vertices": [[0, 0, 0], [10, 0, 0], [10, 0, 10], [0, 0, 10]],
            },
        ]
        source = ShadingSource(
            source_id="B002",
            shading_type=ShadingType.BUILDING,
            height_m=20.0,
            distance_m=30.0,
        )
        results = analyzer.analyze_building("B001", surfaces, [source])
        assert len(results) == 2

    def test_filter_nearby_sources(self):
        from backend.geometry.shading import (
            ShadingAnalyzer,
            ShadingSource,
            ShadingType,
        )
        analyzer = ShadingAnalyzer(max_shading_distance_m=100.0)
        sources = [
            ShadingSource(
                "near", ShadingType.BUILDING,
                height_m=15.0, distance_m=30.0,
            ),
            ShadingSource(
                "far", ShadingType.BUILDING,
                height_m=15.0, distance_m=200.0,
            ),
            ShadingSource(
                "short", ShadingType.BUILDING,
                height_m=3.0, distance_m=10.0,
            ),
        ]
        filtered = analyzer.filter_nearby_sources(sources, reference_height=10.0)
        ids = [s.source_id for s in filtered]
        assert "near" in ids
        assert "far" not in ids
        assert "short" not in ids

    def test_horizon_obstruction_clear(self):
        from backend.geometry.shading import estimate_horizon_obstruction
        result = estimate_horizon_obstruction(
            surface_tilt_deg=30.0,
            surface_azimuth_deg=180.0,
            horizon_angles={"south": 0.0},
        )
        assert result == 0.0

    def test_horizon_obstruction_blocked(self):
        from backend.geometry.shading import estimate_horizon_obstruction
        result = estimate_horizon_obstruction(
            surface_tilt_deg=10.0,
            surface_azimuth_deg=180.0,
            horizon_angles={"south": 50.0},
        )
        assert result > 0.0

    def test_horizon_obstruction_no_data(self):
        from backend.geometry.shading import estimate_horizon_obstruction
        result = estimate_horizon_obstruction(30.0, 180.0, None)
        assert result == 0.0


# =====================================================================
# Backward compatibility regression
# =====================================================================


class TestBackwardCompatibility:
    """Ensure all original behaviors are preserved."""

    def test_basic_roof_extraction(self):
        building = {
            "building_id": "B001",
            "surfaces": [
                {
                    "surface_id": "S001",
                    "vertices": [
                        [0, 0, 10],
                        [20, 0, 10],
                        [20, 20, 10],
                        [0, 20, 10],
                    ],
                }
            ],
        }
        surfaces = extract_surfaces(building)
        assert len(surfaces) == 1
        assert surfaces[0]["surface_type"] == "roof"
        assert surfaces[0]["area_m2"] == pytest.approx(400.0)
        assert surfaces[0]["tilt_deg"] == pytest.approx(0.0)

    def test_facade_classification(self):
        verts = [
            [0, 0, 0],
            [0, 20, 0],
            [0, 20, 10],
            [0, 0, 10],
        ]
        normal = calculate_normal(verts)
        assert classify_surface(normal) == "facade"

    def test_ground_classification(self):
        normal = [0.0, 0.0, -1.0]
        assert classify_surface(normal) == "ground"

    def test_tilt_values(self):
        assert calculate_tilt([0, 0, 1]) == pytest.approx(0.0)
        assert calculate_tilt([1, 0, 0]) == pytest.approx(90.0)
        assert calculate_tilt([1, 0, 1]) == pytest.approx(45.0)

    def test_azimuth_cardinal_directions(self):
        assert calculate_azimuth([0, 1, 0]) == pytest.approx(0.0)   # N
        assert calculate_azimuth([1, 0, 0]) == pytest.approx(90.0)  # E
        assert calculate_azimuth([0, -1, 0]) == pytest.approx(180.0)  # S
        assert calculate_azimuth([-1, 0, 0]) == pytest.approx(270.0)  # W
