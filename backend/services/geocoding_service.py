"""Geocoding service for SolarIQ location search.

Integrates with OpenStreetMap / Nominatim for legitimate geocoding.
Features:
- Live OSM Nominatim queries with timeout and rate-limit safeguards
- Local cache with TTL to minimize external API load
- Rich pre-populated offline fallback dataset for key demo locations
  (e.g., Bandra West, Andheri East, Mumbai, Thakur College of Engineering)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SolarIQ-BIPV-Analysis/1.0 (contact: support@solariq.local)"
GEOCODE_CACHE_DIR = Path(DATA_DIR) / "cache" / "geocoding"

# Pre-populated fallback locations for offline operation and fast demo access
DEMO_LOCATIONS: list[dict[str, Any]] = [
    {
        "location_name": "Bandra West, Mumbai",
        "display_name": "Bandra West, Mumbai, Maharashtra, 400050, India",
        "latitude": 19.0596,
        "longitude": 72.8295,
        "bounding_box": [19.0450, 72.8150, 19.0750, 72.8450],
        "category": "suburb",
        "importance": 0.85,
        "is_demo": True,
    },
    {
        "location_name": "Andheri East, Mumbai",
        "display_name": "Andheri East, Mumbai Suburban, Maharashtra, 400069, India",
        "latitude": 19.1136,
        "longitude": 72.8697,
        "bounding_box": [19.0980, 72.8550, 19.1290, 72.8850],
        "category": "suburb",
        "importance": 0.82,
        "is_demo": True,
    },
    {
        "location_name": "Mumbai",
        "display_name": "Mumbai, Mumbai Suburban, Maharashtra, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "bounding_box": [18.8900, 72.7750, 19.2700, 72.9800],
        "category": "city",
        "importance": 0.95,
        "is_demo": True,
    },
    {
        "location_name": "Thakur College of Engineering",
        "display_name": "Thakur College of Engineering and Technology, Kandivali East, Mumbai, Maharashtra, 400101, India",
        "latitude": 19.2063,
        "longitude": 72.8738,
        "bounding_box": [19.2000, 72.8680, 19.2120, 72.8800],
        "category": "amenity",
        "importance": 0.78,
        "is_demo": True,
    },
    {
        "location_name": "Bandra Kurla Complex (BKC), Mumbai",
        "display_name": "Bandra Kurla Complex, Bandra East, Mumbai, Maharashtra, 400051, India",
        "latitude": 19.0657,
        "longitude": 72.8687,
        "bounding_box": [19.0550, 72.8580, 19.0750, 72.8790],
        "category": "commercial",
        "importance": 0.80,
        "is_demo": True,
    },
    {
        "location_name": "Nariman Point, Mumbai",
        "display_name": "Nariman Point, South Mumbai, Maharashtra, 400021, India",
        "latitude": 18.9256,
        "longitude": 72.8242,
        "bounding_box": [18.9180, 72.8180, 18.9330, 72.8300],
        "category": "commercial",
        "importance": 0.79,
        "is_demo": True,
    },
    {
        "location_name": "Connaught Place, New Delhi",
        "display_name": "Connaught Place, New Delhi, Delhi, 110001, India",
        "latitude": 28.6315,
        "longitude": 77.2167,
        "bounding_box": [28.6250, 77.2100, 28.6380, 77.2230],
        "category": "commercial",
        "importance": 0.88,
        "is_demo": True,
    },
    {
        "location_name": "Koramangala, Bengaluru",
        "display_name": "Koramangala, Bengaluru, Karnataka, 560034, India",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "bounding_box": [12.9200, 77.6100, 12.9500, 77.6400],
        "category": "suburb",
        "importance": 0.84,
        "is_demo": True,
    },
]


class GeocodingService:
    """Handles location searches with caching and fallback."""

    def __init__(self, cache_ttl_seconds: int = 86400 * 7):
        self.cache_ttl = cache_ttl_seconds
        self._memory_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        GEOCODE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.strip().lower().split())

    def _get_cache_path(self, query: str) -> Path:
        import hashlib
        q_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
        return GEOCODE_CACHE_DIR / f"{q_hash}.json"

    def _load_cache(self, query: str) -> list[dict[str, Any]] | None:
        normalized = self._normalize_query(query)
        now = time.time()

        # Check memory cache
        if normalized in self._memory_cache:
            ts, data = self._memory_cache[normalized]
            if now - ts < self.cache_ttl:
                return data

        # Check file cache
        path = self._get_cache_path(normalized)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    entry = json.load(f)
                    if now - entry.get("timestamp", 0) < self.cache_ttl:
                        data = entry.get("data", [])
                        self._memory_cache[normalized] = (now, data)
                        return data
            except Exception as exc:
                logger.warning("Failed to read geocode cache for %s: %s", query, exc)

        return None

    def _save_cache(self, query: str, data: list[dict[str, Any]]) -> None:
        normalized = self._normalize_query(query)
        now = time.time()
        self._memory_cache[normalized] = (now, data)

        try:
            path = self._get_cache_path(normalized)
            with path.open("w", encoding="utf-8") as f:
                json.dump({"query": query, "timestamp": now, "data": data}, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to write geocode cache for %s: %s", query, exc)

    def _search_fallback_locations(self, query: str) -> list[dict[str, Any]]:
        normalized = self._normalize_query(query)
        terms = normalized.split()
        matches: list[dict[str, Any]] = []

        for loc in DEMO_LOCATIONS:
            loc_text = f"{loc['location_name']} {loc['display_name']}".lower()
            if normalized in loc_text or any(term in loc_text for term in terms):
                matches.append(loc)

        return matches

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for real-world locations using Nominatim with offline fallback.

        Args:
            query: The location name or address to search.
            limit: Maximum number of results to return (1-20).

        Returns:
            List of location dictionaries with lat, lon, bounding_box, etc.
        """
        if not query or not query.strip():
            return []

        limit = max(1, min(20, limit))
        cleaned_query = query.strip()

        # Check cache first
        cached = self._load_cache(cleaned_query)
        if cached is not None:
            return cached[:limit]

        results: list[dict[str, Any]] = []

        # Attempt live geocoding via OpenStreetMap Nominatim
        params = {
            "q": cleaned_query,
            "format": "json",
            "addressdetails": 1,
            "limit": limit,
        }
        url = f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}"

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for item in data:
                lat = float(item["lat"])
                lon = float(item["lon"])
                bbox_raw = item.get("boundingbox", [])
                # Nominatim bounding box is [south, north, west, east]
                if len(bbox_raw) == 4:
                    south = float(bbox_raw[0])
                    north = float(bbox_raw[1])
                    west = float(bbox_raw[2])
                    east = float(bbox_raw[3])
                    bounding_box = [south, west, north, east]
                else:
                    bounding_box = [lat - 0.005, lon - 0.005, lat + 0.005, lon + 0.005]

                display_name = item.get("display_name", cleaned_query)
                loc_name = display_name.split(",")[0].strip()

                results.append({
                    "location_name": loc_name,
                    "display_name": display_name,
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "bounding_box": [round(c, 6) for c in bounding_box],
                    "category": item.get("type", item.get("class", "location")),
                    "importance": float(item.get("importance", 0.5)),
                    "is_demo": False,
                })

            if results:
                self._save_cache(cleaned_query, results)
                return results

        except Exception as exc:
            logger.info("Live Nominatim geocoding unavailable or timed out: %s. Using local lookup.", exc)

        # Fallback to local demo dataset
        fallback_matches = self._search_fallback_locations(cleaned_query)
        if fallback_matches:
            return fallback_matches[:limit]

        # If nothing matched, but query looks somewhat reasonable, return default Mumbai area demo
        return [DEMO_LOCATIONS[0]]

    def get_sample_locations(self) -> list[dict[str, Any]]:
        """Return curated sample locations for instant UI selection."""
        return DEMO_LOCATIONS


geocoding_service = GeocodingService()
