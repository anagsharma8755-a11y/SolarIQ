// ─── API Types (matching backend schemas) ───

export interface SurfaceInput {
  surface_id?: string;
  vertices: number[][];
}

export interface BuildingInput {
  building_id: string;
  name?: string;
  surfaces: SurfaceInput[];
}

export interface SurfaceNormal {
  x: number;
  y: number;
  z: number;
}

export interface EnergyPotential {
  usable_area_m2: number;
  estimated_capacity_kw: number;
  estimated_annual_energy_kwh: number;
}

export interface AnalyzedSurface {
  surface_id: string;
  building_id: string;
  area_m2: number;
  normal: SurfaceNormal;
  azimuth_deg: number;
  tilt_deg: number;
  surface_type: string;
  vertices: number[][];
  solar_score: number;
  solar_suitability: string;
  energy_potential: EnergyPotential;
  ml_prediction: Record<string, unknown> | null;
  centroid?: number[] | null;
  bounding_box?: { min_x: number; min_y: number; max_x: number; max_y: number } | null;
}

export interface BuildingAnalysisResponse {
  building_id: string;
  name: string | null;
  surface_count: number;
  total_surface_area_m2: number;
  usable_surface_area_m2: number;
  estimated_capacity_kw: number;
  estimated_annual_energy_kwh: number;
  surfaces: AnalyzedSurface[];
}

export interface CitySummary {
  building_count: number;
  surface_count: number;
  total_surface_area_m2: number;
  total_usable_surface_area_m2: number;
  total_estimated_capacity_kw: number;
  total_estimated_annual_energy_kwh: number;
}

export interface CityAnalysisResponse {
  summary: CitySummary;
  buildings: BuildingAnalysisResponse[];
}

export interface OptimizationResult {
  rank: number;
  building_id: string;
  surface_id: string;
  area_m2: number;
  surface_type: string;
  azimuth_deg: number;
  tilt_deg: number;
  solar_score: number;
  solar_suitability: string;
  usable_area_m2: number;
  estimated_capacity_kw: number;
  estimated_annual_energy_kwh: number;
  composite_score: number;
  recommendation: string;
}

export interface CityOptimizationSummary {
  total_suitable_area_m2: number;
  total_potential_capacity_kw: number;
  total_annual_energy_kwh: number;
  top_buildings: string[];
  top_surfaces: string[];
}

export interface OptimizationResponse {
  total_candidates: number;
  filtered_candidates: number;
  scoring_weights: Record<string, number>;
  city_summary: CityOptimizationSummary | null;
  results: OptimizationResult[];
}

export interface SolarPredictionResponse {
  surface_id: string | null;
  building_id: string | null;
  available: boolean;
  prediction: Record<string, unknown> | null;
  fallback_score: number;
  fallback_suitability: string;
  fallback_energy: {
    usable_area_m2: number;
    estimated_capacity_kw: number;
    estimated_annual_energy_kwh: number;
  };
}

export interface SystemStatus {
  status: string;
  version: string;
  environment: string;
  services: {
    geometry_engine: string;
    solar_engine: string;
    optimization_engine: string;
    ml_engine: string;
    database: string;
  };
  paths: Record<string, unknown>;
}

// ─── Real-World City Analysis & GIS Types ───

export interface LocationSearchResult {
  location_name: string;
  display_name: string;
  latitude: number;
  longitude: number;
  bounding_box: number[];
  category: string;
  importance: number;
  is_demo: boolean;
}

export interface AreaSummary {
  building_count: number;
  surface_count: number;
  total_surface_area_m2: number;
  total_usable_surface_area_m2: number;
  total_estimated_capacity_kw: number;
  total_estimated_annual_energy_kwh: number;
  high_potential_count: number;
  medium_potential_count: number;
  low_potential_count: number;
  average_solar_score: number;
  top_performing_building: string | null;
  top_building_name: string | null;
  capacity_density_kw_per_m2: number;
}

export interface RankedSurfaceResult {
  rank: number;
  building_id: string;
  building_name?: string | null;
  surface_id: string;
  surface_type: string;
  area_m2: number;
  azimuth_deg: number;
  tilt_deg: number;
  solar_score: number;
  solar_suitability: string;
  usable_area_m2: number;
  estimated_capacity_kw: number;
  estimated_annual_energy_kwh: number;
  composite_score: number;
  recommendation: string;
}

export interface GISBuilding {
  building_id: string;
  name: string;
  building_type: string;
  height_m: number;
  height_estimated: boolean;
  levels: number;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  polygon_wgs84: number[][];
  surface_count: number;
  total_surface_area_m2: number;
  usable_surface_area_m2: number;
  estimated_capacity_kw: number;
  estimated_annual_energy_kwh: number;
  max_solar_score: number;
  solar_suitability: string;
  best_surface_id: string | null;
  best_surface_type: string;
  surfaces: AnalyzedSurface[];
}

export interface AreaAnalysisResponse {
  analysis_id: string;
  location_name: string;
  latitude: number;
  longitude: number;
  radius_m: number;
  data_provenance: {
    source: string;
    is_live_data: boolean;
    weather: {
      annual_irradiance_kwh_m2: number;
      avg_temperature_c: number;
      avg_cloud_cover_pct: number;
      weather_condition: string;
      data_source: string;
      is_real_data: boolean;
    };
  };
  summary: AreaSummary;
  buildings: GISBuilding[];
  ranked_surfaces: RankedSurfaceResult[];
  geojson: {
    type: "FeatureCollection";
    features: Array<{
      type: "Feature";
      id: string;
      geometry: {
        type: "Polygon";
        coordinates: number[][][];
      };
      properties: {
        building_id: string;
        name: string;
        height_m: number;
        height_estimated: boolean;
        solar_score: number;
        solar_suitability: string;
        usable_area_m2: number;
        estimated_capacity_kw: number;
        estimated_annual_energy_kwh: number;
        best_surface: string;
        color: string;
      };
    }>;
  };
}

export interface DeploymentPhase {
  phase: number;
  name: string;
  surface_count: number;
  capacity_kw: number;
  annual_energy_kwh: number;
  description: string;
}

export interface AreaOptimizationResponse {
  target_capacity_kw: number | null;
  selected_capacity_kw: number;
  capacity_utilization_pct: number;
  selected_annual_energy_kwh: number;
  selected_usable_area_m2: number;
  annual_co2_offset_tonnes: number;
  selected_surfaces_count: number;
  unselected_surfaces_count: number;
  phases: DeploymentPhase[];
  selected_surfaces: RankedSurfaceResult[];
}

export interface AIInterpretation {
  summary: string;
  recommendations: string[];
  avoidance_guidelines: string;
  disclaimer: string;
}

export interface AIExplanationResponse {
  query: string;
  headline: string;
  calculated_results: string[];
  ai_interpretation: AIInterpretation;
  optimization_context: AreaOptimizationResponse | null;
}

// ─── UI Types ───

export type AppView = "hero" | "map" | "city" | "building" | "analysis";

export type AnalysisStep =
  | "select-building"
  | "analyze-surfaces"
  | "solar-potential"
  | "energy-estimation"
  | "recommendation";

export type CameraState = "city" | "building" | "surface" | "analysis" | "overview";

export interface DemoBuilding {
  building_id: string;
  name: string;
  surfaces: SurfaceInput[];
}
