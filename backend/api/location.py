"""Location search and geocoding endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.schemas.area import LocationSearchResult
from backend.services.geocoding_service import geocoding_service

router = APIRouter(
    tags=["Location Search"],
)


@router.get(
    "/locations/search",
    response_model=list[LocationSearchResult],
    summary="Search real-world locations via OpenStreetMap Nominatim",
)
def search_locations(
    q: str = Query(..., min_length=1, max_length=200, description="Location search query (e.g. 'Bandra West, Mumbai')"),
    limit: int = Query(default=5, ge=1, le=20, description="Max search results"),
) -> list[dict[str, object]]:
    """Search for locations using OSM Nominatim with caching and offline fallback."""
    return geocoding_service.search(query=q, limit=limit)


@router.get(
    "/sample-areas",
    response_model=list[LocationSearchResult],
    summary="Get curated sample locations for instant one-click demo",
)
def get_sample_areas() -> list[dict[str, object]]:
    """Return pre-configured demo areas for instant analysis."""
    return geocoding_service.get_sample_locations()
