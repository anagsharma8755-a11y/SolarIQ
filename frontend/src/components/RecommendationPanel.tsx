import type { OptimizationResponse } from "../lib/types";

export function RecommendationPanel({
  data,
  onClose,
}: {
  data: OptimizationResponse;
  onClose: () => void;
}) {
  const topResult = data.results[0];
  const summary = data.city_summary;

  return (
    <div className="absolute top-16 right-[396px] z-20 w-[340px] pointer-events-auto">
      <div className="glass-panel glow-solar-strong">
        {/* Header */}
        <div className="p-4 border-b border-white/5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">
              SOLAR<span className="text-solar-400">IQ</span> RECOMMENDATION
            </h3>
            <button
              onClick={onClose}
              className="text-dark-400 hover:text-white text-xs"
            >
              ✕
            </button>
          </div>
          <p className="text-[10px] text-dark-300 mt-1">
            AI-optimized surface ranking based on {data.total_candidates} candidates
          </p>
        </div>

        {/* Recommended Installation */}
        {topResult && (
          <div className="p-4 border-b border-white/5">
            <div className="text-[10px] text-dark-400 uppercase tracking-wider">
              Recommended Installation
            </div>
            <div className="text-3xl font-bold text-solar-400 mt-1">
              {topResult.estimated_capacity_kw.toFixed(1)} kWp
            </div>
            <div className="text-xs text-dark-300 mt-1">
              {topResult.estimated_annual_energy_kwh.toFixed(0)} kWh/year
            </div>
          </div>
        )}

        {/* Best Surfaces */}
        <div className="p-4 border-b border-white/5">
          <div className="text-[10px] text-dark-400 uppercase tracking-wider mb-2">
            Best Surfaces
          </div>
          <div className="space-y-2">
            {data.results.slice(0, 5).map((r) => (
              <div
                key={r.surface_id}
                className="flex items-center gap-3 p-2 bg-dark-700/50 rounded"
              >
                <div className="w-6 h-6 rounded-full bg-solar-500/10 flex items-center justify-center text-[10px] font-bold text-solar-400">
                  {r.rank}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-white truncate">
                    {r.surface_id}
                  </div>
                  <div className="text-[10px] text-dark-400">
                    {r.surface_type} · {r.area_m2.toFixed(0)} m²
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-medium text-solar-400">
                    {(r.composite_score * 100).toFixed(0)}
                  </div>
                  <div className="text-[9px] text-dark-400">score</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* City Summary */}
        {summary && (
          <div className="p-4 border-b border-white/5">
            <div className="text-[10px] text-dark-400 uppercase tracking-wider mb-2">
              City Impact
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-lg font-semibold text-white">
                  {summary.total_potential_capacity_kw.toFixed(0)}
                </div>
                <div className="text-[9px] text-dark-400">Total Capacity (kW)</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-white">
                  {(summary.total_annual_energy_kwh / 1000).toFixed(0)}
                </div>
                <div className="text-[9px] text-dark-400">Total Energy (MWh)</div>
              </div>
            </div>
          </div>
        )}

        {/* Scoring Weights */}
        <div className="p-4">
          <div className="text-[10px] text-dark-400 uppercase tracking-wider mb-2">
            Scoring Weights
          </div>
          <div className="space-y-1.5">
            {Object.entries(data.scoring_weights).map(([key, weight]) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-[10px] text-dark-300 flex-1 truncate">
                  {key.replace(/_/g, " ")}
                </span>
                <div className="w-16 h-1 bg-dark-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-solar-500 rounded-full"
                    style={{ width: `${weight * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-dark-400 w-8 text-right">
                  {(weight * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
