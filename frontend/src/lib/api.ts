import type {
  BuildingAnalysisResponse,
  CityAnalysisResponse,
  OptimizationResponse,
  SolarPredictionResponse,
  SystemStatus,
  BuildingInput,
  LocationSearchResult,
  AreaAnalysisResponse,
  AreaOptimizationResponse,
  AIExplanationResponse,
} from "./types";

// In development, Vite proxy forwards /api/* to localhost:8000.
// In production, set VITE_API_URL to the deployed backend origin
// (e.g. https://your-backend.leapcell.app).
// An empty string means same-origin requests.
const BASE = import.meta.env.VITE_API_URL ?? "";

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  health: () => apiGet<{ status: string; version?: string }>("/health"),
  status: () => apiGet<SystemStatus>("/status"),

  // Existing Geometry / Building / City APIs
  analyzeBuilding: (building: BuildingInput) =>
    apiPost<BuildingAnalysisResponse>("/analyze-building", { building }),

  analyzeCity: (buildings: BuildingInput[]) =>
    apiPost<CityAnalysisResponse>("/city-analysis", { buildings }),

  optimize: (buildings: BuildingInput[], limit = 20) =>
    apiPost<OptimizationResponse>(
      `/optimization-routes?limit=${limit}`,
      { buildings }
    ),

  predictSolar: (params: {
    surface_id?: string;
    building_id?: string;
    area_m2: number;
    azimuth_deg: number;
    tilt_deg: number;
    surface_type: string;
    latitude?: number;
    longitude?: number;
  }) => apiPost<SolarPredictionResponse>("/predict-solar", params),

  // Real-World City Analysis & GIS APIs
  searchLocations: (q: string, limit = 5) =>
    apiGet<LocationSearchResult[]>(`/locations/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  getSampleAreas: () =>
    apiGet<LocationSearchResult[]>("/sample-areas"),

  analyzeArea: (params: {
    latitude: number;
    longitude: number;
    radius_m?: number;
    location_name?: string;
    max_buildings?: number;
  }) => apiPost<AreaAnalysisResponse>("/area/analyze", params),

  getAreaById: (analysisId: string) =>
    apiGet<AreaAnalysisResponse>(`/area/${encodeURIComponent(analysisId)}`),

  getAreaMapGeoJSON: (analysisId: string) =>
    apiGet<Record<string, unknown>>(`/area/${encodeURIComponent(analysisId)}/map`),

  optimizeArea: (params: {
    analysis_id: string;
    max_capacity_kw?: number;
    min_solar_score?: number;
    allowed_surface_types?: string[];
    target_metric?: string;
  }) => apiPost<AreaOptimizationResponse>("/area/optimize", params),

  explainAI: (params: {
    analysis_id?: string;
    query: string;
    target_capacity_kw?: number;
    analysis_data?: unknown;
  }) => apiPost<AIExplanationResponse>("/ai/explain", params),
};
