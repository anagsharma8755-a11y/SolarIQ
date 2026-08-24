import type { BuildingAnalysisResponse, AnalyzedSurface, OptimizationResponse } from "../lib/types";

function SuitabilityBadge({ score, label }: { score: number; label: string }) {
  const color =
    score >= 0.8
      ? "text-green-400 bg-green-500/10 border-green-500/20"
      : score >= 0.6
      ? "text-green-300 bg-green-500/10 border-green-500/20"
      : score >= 0.4
      ? "text-solar-400 bg-solar-500/10 border-solar-500/20"
      : score >= 0.2
      ? "text-orange-400 bg-orange-500/10 border-orange-500/20"
      : "text-red-400 bg-red-500/10 border-red-500/20";

  return (
    <span className={`px-2 py-0.5 text-[10px] font-medium rounded border ${color}`}>
      {label}
    </span>
  );
}

function SurfaceRow({
  surface,
  onSelect,
  isOptimized,
}: {
  surface: AnalyzedSurface;
  onSelect: (s: AnalyzedSurface) => void;
  isOptimized?: boolean;
}) {
  return (
    <button
      onClick={() => onSelect(surface)}
      className="w-full text-left p-3 glass-panel-solid hover:bg-dark-700 transition-colors group"
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor:
                surface.surface_type === "roof"
                  ? "#FFB300"
                  : surface.surface_type === "facade"
                  ? "#42A5F5"
                  : "#78909C",
            }}
          />
          <span className="text-xs font-medium text-white uppercase">
            {surface.surface_type}
          </span>
          {isOptimized && (
            <span className="text-[9px] text-solar-400 font-bold">★ TOP</span>
          )}
        </div>
        <SuitabilityBadge
          score={surface.solar_score}
          label={surface.solar_suitability}
        />
      </div>
      <div className="text-[10px] text-dark-300 font-mono">{surface.surface_id}</div>
      <div className="grid grid-cols-3 gap-2 mt-2">
        <div>
          <div className="text-xs text-white">{surface.area_m2.toFixed(0)} m²</div>
          <div className="text-[9px] text-dark-400">Area</div>
        </div>
        <div>
          <div className="text-xs text-white">{(surface.solar_score * 100).toFixed(0)}%</div>
          <div className="text-[9px] text-dark-400">Score</div>
        </div>
        <div>
          <div className="text-xs text-white">
            {surface.energy_potential.estimated_capacity_kw.toFixed(1)}
          </div>
          <div className="text-[9px] text-dark-400">kW</div>
        </div>
      </div>
    </button>
  );
}

export function BuildingPanel({
  data,
  onSelectSurface,
  onOptimize,
  onBack,
  optimization,
}: {
  data: BuildingAnalysisResponse;
  onSelectSurface: (s: AnalyzedSurface) => void;
  onOptimize: () => void;
  onBack: () => void;
  optimization: OptimizationResponse | null;
}) {
  const optimizedIds = new Set(
    optimization?.results.map((r) => r.surface_id) ?? []
  );

  // Sort surfaces by score
  const sortedSurfaces = [...data.surfaces].sort(
    (a, b) => b.solar_score - a.solar_score
  );

  const avgScore =
    data.surfaces.reduce((sum, s) => sum + s.solar_score, 0) /
    data.surfaces.length;

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={onBack}
            className="text-xs text-dark-300 hover:text-white transition-colors mb-1"
          >
            ← Back to city
          </button>
          <h2 className="text-lg font-semibold text-white">
            {data.name || data.building_id}
          </h2>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-solar-400">
            {(avgScore * 100).toFixed(0)}%
          </div>
          <div className="text-[10px] text-dark-300 uppercase">Avg Score</div>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="metric-card">
          <span className="metric-value text-xl">{data.surface_count}</span>
          <span className="metric-label">Surfaces</span>
        </div>
        <div className="metric-card">
          <span className="metric-value text-xl">
            {data.total_surface_area_m2.toFixed(0)}
          </span>
          <span className="metric-label">Total Area (m²)</span>
        </div>
        <div className="metric-card">
          <span className="metric-value text-xl">
            {data.estimated_capacity_kw.toFixed(1)}
          </span>
          <span className="metric-label">Capacity (kW)</span>
        </div>
        <div className="metric-card">
          <span className="metric-value text-xl">
            {(data.estimated_annual_energy_kwh / 1000).toFixed(1)}
          </span>
          <span className="metric-label">Energy (MWh/yr)</span>
        </div>
      </div>

      {/* CO2 reduction */}
      <div className="glass-panel p-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500 text-lg">
          🌱
        </div>
        <div>
          <div className="text-sm font-medium text-white">
            {(data.estimated_annual_energy_kwh * 0.00075).toFixed(0)} t CO₂/year
          </div>
          <div className="text-[10px] text-dark-300">
            Environmental Impact (at 0.75 kg CO₂/kWh grid factor)
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button onClick={onOptimize} className="btn-primary flex-1 text-xs">
          ⚡ Run Optimization
        </button>
      </div>

      {/* Surfaces */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-dark-200">Surfaces</h3>
          <span className="text-[10px] text-dark-400">
            Sorted by solar score
          </span>
        </div>
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {sortedSurfaces.map((s) => (
            <SurfaceRow
              key={s.surface_id}
              surface={s}
              onSelect={onSelectSurface}
              isOptimized={optimizedIds.has(s.surface_id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
