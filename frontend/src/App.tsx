import { useState, useCallback, useEffect, Suspense, lazy } from "react";
import { api } from "./lib/api";
import type {
  AppView,
  AnalysisStep,
  CameraState,
  BuildingAnalysisResponse,
  CityAnalysisResponse,
  OptimizationResponse,
  AnalyzedSurface,
  DemoBuilding,
  AreaAnalysisResponse,
  GISBuilding,
  LocationSearchResult,
} from "./lib/types";
import { DEMO_BUILDINGS, toBuildingInput, getAllBuildingInputs } from "./lib/demoData";
import { LoadingScreen } from "./components/LoadingScreen";
import { HeroScreen } from "./components/HeroScreen";
import { TopNav } from "./components/TopNav";
import { BuildingPanel } from "./components/BuildingPanel";
import { SurfaceDetailPanel } from "./components/SurfaceDetailPanel";
import { AnalysisDashboard } from "./components/AnalysisDashboard";
import { RecommendationPanel } from "./components/RecommendationPanel";
import { StepFlow } from "./components/StepFlow";
import { MapView } from "./components/MapView";
import { LocationSearchBar } from "./components/LocationSearchBar";
import { AreaDashboard } from "./components/AreaDashboard";
import { AIExplainerPanel } from "./components/AIExplainerPanel";
import { CapacityOptimizerModal } from "./components/CapacityOptimizerModal";

// Lazy-loaded heavy components — split into separate chunks
const ThreeViewer = lazy(() => import("./components/ThreeViewer"));
const AnalysisCharts = lazy(() => import("./components/AnalysisCharts"));

export default function App() {
  const [view, setView] = useState<AppView>("hero");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Real-World Area & GIS State
  const [mapCenter, setMapCenter] = useState<[number, number]>([19.0596, 72.8295]); // Bandra West, Mumbai
  const [radiusMeters, setRadiusMeters] = useState<number>(400);
  const [areaData, setAreaData] = useState<AreaAnalysisResponse | null>(null);
  const [viewMode, setViewMode] = useState<"map" | "3d">("map");

  // Synthetic / Sample Data (retained for backward compatibility)
  const [cityData, setCityData] = useState<CityAnalysisResponse | null>(null);
  const [selectedBuilding, setSelectedBuilding] = useState<BuildingAnalysisResponse | null>(null);
  const [selectedGISBuilding, setSelectedGISBuilding] = useState<GISBuilding | null>(null);
  const [selectedSurface, setSelectedSurface] = useState<AnalyzedSurface | null>(null);
  const [optimizationData, setOptimizationData] = useState<OptimizationResponse | null>(null);

  // Modals & Overlays
  const [showAIExplainer, setShowAIExplainer] = useState(false);
  const [showCapacityOptimizer, setShowCapacityOptimizer] = useState(false);

  // UI state
  const [cameraState, setCameraState] = useState<CameraState>("city");
  const [currentStep, setCurrentStep] = useState<AnalysisStep>("select-building");
  const [heatmapMode, setHeatmapMode] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Initial real-world data load (Bandra West, Mumbai demo area)
  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await api.health();
        // Load initial real-world area analysis for Bandra West
        const area = await api.analyzeArea({
          latitude: 19.0596,
          longitude: 72.8295,
          radius_m: 400,
          location_name: "Bandra West, Mumbai",
        });

        // Also load legacy city data for 3D demo fallback
        const city = await api.analyzeCity(getAllBuildingInputs());

        if (!cancelled) {
          setAreaData(area);
          setCityData(city);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setApiError(
            err instanceof Error ? err.message : "Failed to connect to backend"
          );
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, []);

  // Handle location search and real-world area analysis
  const handleSelectLocation = useCallback(
    async (loc: LocationSearchResult, radiusM: number) => {
      setAnalyzing(true);
      setApiError(null);
      setMapCenter([loc.latitude, loc.longitude]);
      setRadiusMeters(radiusM);
      try {
        const area = await api.analyzeArea({
          latitude: loc.latitude,
          longitude: loc.longitude,
          radius_m: radiusM,
          location_name: loc.location_name,
        });
        setAreaData(area);
        setSelectedGISBuilding(null);
        setSelectedBuilding(null);
        setSelectedSurface(null);
        setView("map");
      } catch (err) {
        setApiError(err instanceof Error ? err.message : "Area analysis failed");
      } finally {
        setAnalyzing(false);
      }
    },
    []
  );

  // Handle building selection from real GIS Map
  const handleSelectGISBuilding = useCallback(
    async (building: GISBuilding) => {
      setSelectedGISBuilding(building);
      setSelectedSurface(null);
      // Convert to BuildingAnalysisResponse format for shared detail panels
      const converted: BuildingAnalysisResponse = {
        building_id: building.building_id,
        name: building.name,
        surface_count: building.surface_count,
        total_surface_area_m2: building.total_surface_area_m2,
        usable_surface_area_m2: building.usable_surface_area_m2,
        estimated_capacity_kw: building.estimated_capacity_kw,
        estimated_annual_energy_kwh: building.estimated_annual_energy_kwh,
        surfaces: building.surfaces,
      };
      setSelectedBuilding(converted);
      setCurrentStep("analyze-surfaces");
    },
    []
  );

  // Handle 3D building selection (ThreeViewer)
  const handleSelectBuilding = useCallback(async (building: DemoBuilding) => {
    setAnalyzing(true);
    setApiError(null);
    try {
      const result = await api.analyzeBuilding(toBuildingInput(building));
      setSelectedBuilding(result);
      setSelectedSurface(null);
      setView("building");
      setCameraState("building");
      setCurrentStep("analyze-surfaces");
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  }, []);

  const handleSelectSurface = useCallback(async (surface: AnalyzedSurface) => {
    setSelectedSurface(surface);
    setCameraState("surface");
    setCurrentStep("solar-potential");
    setHeatmapMode(true);
  }, []);

  const handleRunOptimization = useCallback(async () => {
    if (!cityData) return;
    setAnalyzing(true);
    setApiError(null);
    try {
      const result = await api.optimize(getAllBuildingInputs(), 20);
      setOptimizationData(result);
      setCurrentStep("recommendation");
      setCameraState("analysis");
    } catch (err) {
      setApiError(err instanceof Error ? err.message : "Optimization failed");
    } finally {
      setAnalyzing(false);
    }
  }, [cityData]);

  const handleGoHome = useCallback(() => {
    setView("hero");
    setSelectedBuilding(null);
    setSelectedGISBuilding(null);
    setSelectedSurface(null);
    setOptimizationData(null);
    setHeatmapMode(false);
    setCameraState("city");
    setCurrentStep("select-building");
  }, []);

  const handleStartAnalysis = useCallback(() => {
    setView("map");
    setViewMode("map");
  }, []);

  if (loading) return <LoadingScreen />;

  if (view === "hero") {
    return <HeroScreen onStart={handleStartAnalysis} error={apiError} />;
  }

  return (
    <div className="h-full flex flex-col bg-dark-950">
      <TopNav
        view={view}
        onHome={handleGoHome}
        onNavigate={(v) => {
          setView(v);
          if (v === "map") setViewMode("map");
          if (v === "city") setViewMode("3d");
        }}
      />

      {/* Location Search Bar Header */}
      <div className="px-4 py-2 bg-dark-900/60 border-b border-white/5 z-10">
        <LocationSearchBar
          onSelectLocation={handleSelectLocation}
          onRadiusChange={(r) => {
            setRadiusMeters(r);
            if (areaData) {
              handleSelectLocation(
                {
                  location_name: areaData.location_name,
                  display_name: areaData.location_name,
                  latitude: mapCenter[0],
                  longitude: mapCenter[1],
                  bounding_box: [],
                  category: "suburb",
                  importance: 0.85,
                  is_demo: false,
                },
                r
              );
            }
          }}
          radiusMeters={radiusMeters}
          analyzing={analyzing}
          viewMode={viewMode}
          onToggleViewMode={(mode) => setViewMode(mode)}
        />
      </div>

      <div className="flex-1 flex overflow-hidden relative">
        {/* Main Central Canvas (GIS Map or 3D LOD-1 Mesh) */}
        <div className="flex-1 relative">
          {viewMode === "map" ? (
            <MapView
              center={mapCenter}
              radiusMeters={radiusMeters}
              areaData={areaData}
              selectedBuilding={selectedGISBuilding}
              onSelectBuilding={handleSelectGISBuilding}
            />
          ) : (
            <Suspense
              fallback={
                <div className="h-full flex items-center justify-center bg-dark-950">
                  <div className="text-dark-300">Loading 3D viewer...</div>
                </div>
              }
            >
              <ThreeViewer
                buildings={DEMO_BUILDINGS}
                analysisData={selectedBuilding}
                cityData={cityData}
                cameraState={cameraState}
                heatmapMode={heatmapMode}
                selectedSurfaceId={selectedSurface?.surface_id ?? null}
                onSelectBuilding={handleSelectBuilding}
                onSelectSurface={handleSelectSurface}
              />
            </Suspense>
          )}

          {/* Step flow overlay */}
          <div className="absolute bottom-4 left-4 right-4 pointer-events-none z-10">
            <StepFlow currentStep={currentStep} />
          </div>

          {/* Error toast */}
          {apiError && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 glass-panel px-4 py-3 text-sm text-red-400 pointer-events-auto z-50">
              {apiError}
              <button
                onClick={() => setApiError(null)}
                className="ml-3 text-dark-300 hover:text-white"
              >
                ✕
              </button>
            </div>
          )}

          {/* Analyzing overlay — professional scanning state */}
          {analyzing && (
            <div className="absolute inset-0 bg-dark-950/70 flex items-center justify-center pointer-events-none z-40">
              <div className="glass-panel-solid px-8 py-6 flex flex-col items-center gap-4 min-w-[320px]">
                {/* Orbital scan ring */}
                <div className="relative w-14 h-14">
                  <div className="absolute inset-0 border-2 border-solar-500/20 rounded-full" />
                  <div className="absolute inset-0 border-2 border-t-solar-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin" />
                  <div className="absolute inset-2 border border-solar-500/10 rounded-full animate-spin-slow" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-3 h-3 bg-solar-500 rounded-full animate-pulse-glow" />
                  </div>
                </div>
                <div className="text-center space-y-1">
                  <div className="text-xs font-semibold text-solar-400 uppercase tracking-widest">
                    Analyzing Solar Potential
                  </div>
                  <div className="text-[11px] text-dark-300">
                    Retrieving OSM geometry & atmospheric irradiance...
                  </div>
                </div>
                {/* Scan progress bar */}
                <div className="w-full h-1 bg-dark-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-solar-600 to-solar-400 rounded-full animate-pulse-glow" style={{ width: '60%' }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Side Panel: Area Dashboard, Building Details, or Surface Details */}
        <div className="w-[380px] bg-dark-900 border-l border-white/5 overflow-y-auto flex-shrink-0 z-20 side-panel-scroll">
          {selectedSurface ? (
            <SurfaceDetailPanel
              surface={selectedSurface}
              onClose={() => {
                setSelectedSurface(null);
                setCameraState("building");
                setHeatmapMode(false);
                setCurrentStep("analyze-surfaces");
              }}
            />
          ) : selectedBuilding ? (
            <BuildingPanel
              data={selectedBuilding}
              onSelectSurface={handleSelectSurface}
              onOptimize={handleRunOptimization}
              onBack={() => {
                setSelectedBuilding(null);
                setSelectedGISBuilding(null);
                setCameraState("city");
                setCurrentStep("select-building");
              }}
              optimization={optimizationData}
            />
          ) : areaData ? (
            <AreaDashboard
              data={areaData}
              onSelectBuilding={handleSelectGISBuilding}
              onOpenAIExplainer={() => setShowAIExplainer(true)}
              onOpenCapacityOptimizer={() => setShowCapacityOptimizer(true)}
            />
          ) : cityData ? (
            <CityPanel
              data={cityData}
              onSelectBuilding={handleSelectBuilding}
            />
          ) : (
            <div className="p-6 flex flex-col items-center justify-center h-full text-center space-y-4">
              <div className="w-12 h-12 rounded-xl bg-dark-800 border border-white/5 flex items-center justify-center text-2xl">
                🗺️
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Select a Location</h3>
                <p className="text-xs text-dark-300 mt-1">
                  Search for a real-world location above to begin solar analysis
                </p>
              </div>
              <div className="text-[10px] text-dark-400">
                Try: Mumbai, Delhi, Bengaluru, or Bandra Kurla Complex
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Explainer Modal Overlay */}
      {showAIExplainer && areaData && (
        <div className="fixed inset-0 z-50 bg-dark-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-2xl">
            <AIExplainerPanel
              areaData={areaData}
              onClose={() => setShowAIExplainer(false)}
            />
          </div>
        </div>
      )}

      {/* Capacity Constraint Optimizer Modal */}
      {showCapacityOptimizer && areaData && (
        <CapacityOptimizerModal
          areaData={areaData}
          onClose={() => setShowCapacityOptimizer(false)}
        />
      )}

      {/* Dashboard overlay for analysis view */}
      {view === "building" && selectedBuilding && (
        <AnalysisDashboard
          building={selectedBuilding}
          optimization={optimizationData}
          visible={
            currentStep === "energy-estimation" ||
            currentStep === "recommendation"
          }
          onRunOptimization={handleRunOptimization}
        />
      )}

      {/* Charts overlay */}
      {selectedBuilding && (
        <Suspense fallback={null}>
          <AnalysisCharts
            building={selectedBuilding}
            optimization={optimizationData}
            visible={view === "building"}
          />
        </Suspense>
      )}

      {/* Legacy Recommendation panel */}
      {optimizationData && currentStep === "recommendation" && (
        <RecommendationPanel
          data={optimizationData}
          onClose={() => setCurrentStep("energy-estimation")}
        />
      )}
    </div>
  );
}

// ─── City Panel (side panel for sample dataset city view) ───

import type { CitySummary } from "./lib/types";

function CityPanel({
  data,
  onSelectBuilding,
}: {
  data: CityAnalysisResponse;
  onSelectBuilding: (b: DemoBuilding) => void;
}) {
  const summary: CitySummary = data.summary;
  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">City 3D Overview</h2>
        <p className="text-sm text-dark-300 mt-1">Select a building to inspect</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="metric-card">
          <span className="metric-value">{summary.building_count}</span>
          <span className="metric-label">Buildings</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{summary.surface_count}</span>
          <span className="metric-label">Surfaces</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">
            {summary.total_estimated_capacity_kw.toFixed(0)}
          </span>
          <span className="metric-label">Capacity (kW)</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">
            {(summary.total_estimated_annual_energy_kwh / 1000).toFixed(1)}
          </span>
          <span className="metric-label">Energy (MWh/yr)</span>
        </div>
      </div>

      <div className="space-y-2">
        {data.buildings.map((b) => (
          <button
            key={b.building_id}
            onClick={() => {
              const demo = DEMO_BUILDINGS.find(
                (d) => d.building_id === b.building_id
              );
              if (demo) onSelectBuilding(demo);
            }}
            className="w-full glass-panel-solid p-3 text-left hover:bg-dark-700 transition-colors group"
          >
            <div className="flex justify-between items-center">
              <div>
                <div className="text-sm font-medium text-white group-hover:text-solar-400 transition-colors">
                  {b.name || b.building_id}
                </div>
                <div className="text-xs text-dark-300 mt-0.5">
                  {b.surface_count} surfaces · {b.total_surface_area_m2.toFixed(0)} m²
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-solar-400">
                  {b.estimated_capacity_kw.toFixed(1)} kW
                </div>
                <div className="text-xs text-dark-300">
                  {b.estimated_annual_energy_kwh.toFixed(0)} kWh/yr
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
