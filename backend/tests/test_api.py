from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


SAMPLE_BUILDING = {
    "building_id": "TEST-001",
    "name": "Test Building",
    "surfaces": [
        {
            "surface_id": "TEST-001-S001",
            "vertices": [
                [0, 0, 10],
                [20, 0, 10],
                [20, 20, 10],
                [0, 20, 10],
            ],
        },
        {
            "surface_id": "TEST-001-S002",
            "vertices": [
                [0, 0, 0],
                [20, 0, 0],
                [20, 0, 10],
                [0, 0, 10],
            ],
        },
    ],
}


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["project"] == "SolarIQ"
    assert data["status"] == "running"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_analyze_building():
    response = client.post(
        "/analyze-building",
        json={
            "building": SAMPLE_BUILDING
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["building_id"] == "TEST-001"
    assert data["surface_count"] == 2

    assert data["total_surface_area_m2"] > 0

    assert len(data["surfaces"]) == 2


def test_analyze_building_surface_data():
    response = client.post(
        "/analyze-building",
        json={
            "building": SAMPLE_BUILDING
        },
    )

    assert response.status_code == 200

    surfaces = response.json()["surfaces"]

    roof = surfaces[0]

    assert roof["surface_id"] == "TEST-001-S001"

    assert roof["area_m2"] == 400.0

    assert roof["surface_type"] == "roof"

    assert roof["tilt_deg"] == 0.0

    assert "normal" in roof

    assert "solar_score" in roof

    assert "solar_suitability" in roof

    assert "energy_potential" in roof


def test_city_analysis():
    second_building = {
        **SAMPLE_BUILDING,
        "building_id": "TEST-002",
    }

    response = client.post(
        "/city-analysis",
        json={
            "buildings": [
                SAMPLE_BUILDING,
                second_building,
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    summary = data["summary"]

    assert summary["building_count"] == 2

    assert summary["surface_count"] == 4

    assert summary[
        "total_surface_area_m2"
    ] > 0

    assert summary[
        "total_usable_surface_area_m2"
    ] > 0

    assert summary[
        "total_estimated_capacity_kw"
    ] > 0

    assert len(data["buildings"]) == 2


def test_optimization_routes():
    response = client.post(
        "/optimization-routes",
        json={
            "buildings": [
                SAMPLE_BUILDING
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_candidates"] > 0

    results = data["results"]

    assert len(results) <= 5

    assert results[0]["rank"] == 1

    assert "building_id" in results[0]

    assert "surface_id" in results[0]

    assert "solar_score" in results[0]

    assert "estimated_capacity_kw" in results[0]


def test_optimization_ranking():
    response = client.post(
        "/optimization-routes",
        json={
            "buildings": [
                SAMPLE_BUILDING
            ]
        },
    )

    assert response.status_code == 200

    results = response.json()["results"]

    scores = [
        result["solar_score"]
        for result in results
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_custom_optimization_limit():
    response = client.post(
        "/optimization-routes?limit=1",
        json={
            "buildings": [
                SAMPLE_BUILDING
            ]
        },
    )

    assert response.status_code == 200

    results = response.json()["results"]

    assert len(results) == 1

    assert results[0]["rank"] == 1


def test_invalid_building():
    response = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "INVALID",
                "surfaces": [],
            }
        },
    )

    assert response.status_code == 422


def test_missing_building_id():
    response = client.post(
        "/analyze-building",
        json={
            "building": {
                "surfaces": [
                    {
                        "vertices": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, 10, 0],
                        ]
                    }
                ]
            }
        },
    )

    assert response.status_code == 422


def test_malformed_surface():
    response = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "BAD-001",
                "surfaces": [
                    {
                        "surface_id": "BAD-S001",
                        "vertices": [
                            [0, 0, 0],
                            [10, 0, 0],
                        ],
                    }
                ],
            }
        },
    )

    assert response.status_code == 422


def test_empty_city():
    response = client.post(
        "/city-analysis",
        json={
            "buildings": []
        },
    )

    assert response.status_code == 422


def test_invalid_optimization_limit():
    response = client.post(
        "/optimization-routes?limit=0",
        json={
            "buildings": [
                SAMPLE_BUILDING
            ]
        },
    )

    assert response.status_code == 422


# ------------------------------------------------------------------
# /status endpoint tests
# ------------------------------------------------------------------


def test_status_200():
    response = client.get("/status")

    assert response.status_code == 200


def test_status_healthy():
    data = client.get("/status").json()

    assert data["status"] == "healthy"


def test_status_version_exists():
    data = client.get("/status").json()

    assert "version" in data


def test_status_services_exists():
    data = client.get("/status").json()

    assert "services" in data


def test_status_geometry_engine():
    data = client.get("/status").json()

    assert data["services"]["geometry_engine"] == "available"


def test_status_solar_engine():
    data = client.get("/status").json()

    assert data["services"]["solar_engine"] == "available"


def test_status_optimization_engine():
    data = client.get("/status").json()

    assert data["services"]["optimization_engine"] == "available"


def test_status_ml_engine():
    data = client.get("/status").json()

    assert data["services"]["ml_engine"] in ("fallback", "connected")


def test_root_has_version():
    data = client.get("/").json()

    assert "version" in data
    assert data["version"] == "0.1.0"


def test_collinear_vertices_returns_422():
    response = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "COLL-001",
                "surfaces": [
                    {
                        "surface_id": "COLL-S001",
                        "vertices": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [20, 0, 0],
                        ],
                    }
                ],
            }
        },
    )

    assert response.status_code == 422


def test_non_numeric_vertices_returns_422():
    response = client.post(
        "/analyze-building",
        json={
            "building": {
                "building_id": "NAN-001",
                "surfaces": [
                    {
                        "surface_id": "NAN-S001",
                        "vertices": [
                            [0, 0, 0],
                            [10, 0, 0],
                            [10, "abc", 0],
                        ],
                    }
                ],
            }
        },
    )

    assert response.status_code == 422


def test_status_full_response():
    data = client.get("/status").json()

    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "environment" in data
    assert isinstance(data["services"], dict)
    assert "database" in data["services"]
    assert "paths" in data