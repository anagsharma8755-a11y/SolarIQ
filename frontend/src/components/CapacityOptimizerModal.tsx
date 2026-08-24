import { useState, useCallback, useRef, useEffect } from "react";
import { api } from "../lib/api";
import type { AreaAnalysisResponse, AreaOptimizationResponse } from "../lib/types";
import { staggerFadeIn, slideInUp } from "../lib/animations";

interface CapacityOptimizerModalProps {
  areaData: AreaAnalysisResponse;
  onClose: () => void;
}

export function CapacityOptimizerModal({
  areaData,
  onClose,
}: CapacityOptimizerModalProps) {
  const [targetKw, setTargetKw] = useState(500);
  const [minScore, setMinScore] = useState(0.40);
  const [surfaceTypes, setSurfaceTypes] = useState<string[]>(["roof", "facade"]);
  const [result, setResult] = useState<AreaOptimizationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const resultsRef = useRef<HTMLDivElement>(null);

  const runOptimization = useCallback(async (kw: number, score: number, types: string[]) => {
    setLoading(true);
    try {
      const res = await api.optimizeArea({
        analysis_id: areaData.analysis_id,
        max_capacity_kw: kw,
        min_solar_score: score,
        allowed_surface_types: types,
      });
      setResult(res);
    } catch (err) {
      console.error("Optimization failed:", err);
    } finally {
      setLoading(false);
    }
  }, [areaData.analysis_id]);

  // Run optimization on mount
  useEffect(() => {
    runOptimization(targetKw, minScore, surfaceTypes);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const debouncedOptimize = useCallback(
    (kw: number, score: number, types: string[]) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => runOptimization(kw, score, types), 400);
    },
    [runOptimization]
  );

  // Animate results when they change
  useEffect(() => {
    if (!result || !resultsRef.current) return;
    const cleanup = staggerFadeIn(
      Array.from(resultsRef.current.querySelectorAll("[data-result]")) as HTMLElement[],
      { duration: 350, staggerDelay: 50, startDelay: 50 }
    );
    return cleanup;
  }, [result]);

  return (
    <div className="fixed inset-0 z-50 bg-dark-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="glass-panel-solid w-full max-w-2xl rounded-2xl p-6 border border-white/10 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-solar-500/20 border border-solar-500/30 flex items-center justify-center text-solar-400 font-bold">
              ⚡
            </div>
            <div>
              <h3 className="text-base font-bold text-white">
                Capacity & Budget-Constrained Optimizer
              </h3>
              <p className="text-xs text-dark-300">
                Maximize clean energy output subject to target capacity ceiling
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-dark-400 hover:text-white p-1 rounded-md transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Constraint Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-dark-900/90 p-4 rounded-xl border border-white/10 text-xs">
          {/* Target Capacity Slider */}
          <div className="space-y-1.5 sm:col-span-2">
            <div className="flex justify-between">
              <label className="font-semibold text-white">
                Target Capacity Ceiling:
              </label>
              <span className="font-mono text-solar-400 font-bold">
                {targetKw} kW
              </span>
            </div>
            <input
              type="range"
              min={50}
              max={2000}
              step={25}
              value={targetKw}
              onChange={(e) => {
                const val = Number(e.target.value);
                setTargetKw(val);
                debouncedOptimize(val, minScore, surfaceTypes);
              }}
              className="w-full accent-solar-500 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-dark-400">
              <span>50 kW</span>
              <span>500 kW</span>
              <span>1000 kW</span>
              <span>2000 kW</span>
            </div>
          </div>

          {/* Surface Type Filters */}
          <div className="space-y-1.5">
            <label className="font-semibold text-white block">
              Allowed Surfaces:
            </label>
            <div className="flex flex-col gap-1 text-[11px] text-dark-200">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={surfaceTypes.includes("roof")}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...surfaceTypes, "roof"]
                      : surfaceTypes.length > 1 ? surfaceTypes.filter((t) => t !== "roof") : surfaceTypes;
                    setSurfaceTypes(next);
                    debouncedOptimize(targetKw, minScore, next);
                  }}
                  className="rounded bg-dark-800 text-solar-500 focus:ring-0"
                />
                <span>Rooftops</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={surfaceTypes.includes("facade")}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...surfaceTypes, "facade"]
                      : surfaceTypes.length > 1 ? surfaceTypes.filter((t) => t !== "facade") : surfaceTypes;
                    setSurfaceTypes(next);
                    debouncedOptimize(targetKw, minScore, next);
                  }}
                  className="rounded bg-dark-800 text-solar-500 focus:ring-0"
                />
                <span>BIPV Facades</span>
              </label>
            </div>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center py-4 gap-3">
            <div className="w-4 h-4 border-2 border-solar-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-dark-300">Computing optimal deployment...</span>
          </div>
        )}

        {/* Optimization Metrics Summary */}
        {result && !loading && (
          <div ref={resultsRef} className="space-y-4">
            <div data-result className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="metric-card bg-dark-900/90 p-3 rounded-xl border border-white/10">
                <span className="metric-value text-lg font-bold text-solar-400">
                  {result.selected_capacity_kw.toFixed(1)} kW
                </span>
                <span className="metric-label text-[10px] text-dark-300">
                  Selected ({result.capacity_utilization_pct}% target)
                </span>
              </div>
              <div className="metric-card bg-dark-900/90 p-3 rounded-xl border border-white/10">
                <span className="metric-value text-lg font-bold text-emerald-400">
                  {(result.selected_annual_energy_kwh / 1000).toFixed(1)} MWh
                </span>
                <span className="metric-label text-[10px] text-dark-300">
                  Annual Generation
                </span>
              </div>
              <div className="metric-card bg-dark-900/90 p-3 rounded-xl border border-white/10">
                <span className="metric-value text-lg font-bold text-cyan-400">
                  {result.annual_co2_offset_tonnes.toFixed(1)} t
                </span>
                <span className="metric-label text-[10px] text-dark-300">
                  CO₂ Offset / Year
                </span>
              </div>
              <div className="metric-card bg-dark-900/90 p-3 rounded-xl border border-white/10">
                <span className="metric-value text-lg font-bold text-white">
                  {result.selected_surfaces_count}
                </span>
                <span className="metric-label text-[10px] text-dark-300">
                  Surfaces Chosen
                </span>
              </div>
            </div>

            {/* Phased Deployment Strategy */}
            <div data-result className="space-y-2">
              <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                Recommended Deployment Phases
              </h4>
              <div className="space-y-2">
                {result.phases.map((phase) => (
                  <div
                    key={phase.phase}
                    className="p-3 bg-dark-900/90 rounded-xl border border-white/10 flex items-center justify-between gap-4 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-solar-400">
                        Phase {phase.phase}: {phase.name}
                      </div>
                      <p className="text-[11px] text-dark-300 mt-0.5">
                        {phase.description} ({phase.surface_count} surfaces)
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="font-bold text-white">
                        {phase.capacity_kw} kW
                      </div>
                      <div className="text-[10px] text-emerald-400 font-mono">
                        {(phase.annual_energy_kwh / 1000).toFixed(1)} MWh/yr
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end pt-2 border-t border-white/10">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-solar-500 hover:bg-solar-600 text-dark-950 font-semibold text-xs rounded-lg transition-all"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  );
}
