import { useState, useEffect, useRef } from "react";
import type { AreaAnalysisResponse, GISBuilding } from "../lib/types";
import { countUp, staggerFadeIn } from "../lib/animations";

interface AreaDashboardProps {
  data: AreaAnalysisResponse;
  onSelectBuilding: (building: GISBuilding) => void;
  onOpenAIExplainer: () => void;
  onOpenCapacityOptimizer: () => void;
}

function AnimatedMetric({
  value,
  decimals,
  suffix,
  className,
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const cleanup = countUp(ref.current, value, {
      duration: 1200,
      decimals: decimals ?? 0,
      suffix: suffix ?? "",
    });
    return cleanup;
  }, [value, decimals, suffix]);

  return <span ref={ref} className={className}>0</span>;
}

export function AreaDashboard({
  data,
  onSelectBuilding,
  onOpenAIExplainer,
  onOpenCapacityOptimizer,
}: AreaDashboardProps) {
  const [activeTab, setActiveTab] = useState<"buildings" | "surfaces">("buildings");
  const summary = data.summary;
  const prov = data.data_provenance;
  const metricsRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Stagger entrance animation for KPI cards
  useEffect(() => {
    if (!metricsRef.current) return;
    const cleanup = staggerFadeIn(
      Array.from(metricsRef.current.querySelectorAll("[data-metric]")) as HTMLElement[],
      { duration: 400, staggerDelay: 60, startDelay: 100 }
    );
    return cleanup;
  }, [data.analysis_id]);

  // Stagger entrance for list items
  useEffect(() => {
    if (!listRef.current) return;
    const cleanup = staggerFadeIn(
      Array.from(listRef.current.querySelectorAll("[data-list-item]")) as HTMLElement[],
      { duration: 350, staggerDelay: 40, startDelay: 200 }
    );
    return cleanup;
  }, [data.analysis_id, activeTab]);

  return (
    <div className="p-4 space-y-4">
      {/* Area Title & Provenance */}
      <div data-metric className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white truncate max-w-[220px]">
          {data.location_name}
        </h2>
        <span
          className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
            prov.is_live_data
              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
              : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
          }`}
        >
          {prov.is_live_data ? "● LIVE OSM" : "● DEMO DATA"}
        </span>
      </div>

      <div data-metric className="text-xs text-dark-300 mt-0.5">
        {summary.building_count} buildings · {data.radius_m}m radius
      </div>

      {/* Atmospheric Context */}
      {prov.weather && (
        <div data-metric className="bg-dark-800/80 p-2.5 rounded-lg border border-white/5 flex items-center justify-between text-xs text-dark-200">
          <div className="flex items-center gap-1.5">
            <span>☀️</span>
            <span>{prov.weather.annual_irradiance_kwh_m2} kWh/m² · {prov.weather.weather_condition}</span>
          </div>
          <div className="text-dark-300 text-[11px]">
            {prov.weather.avg_temperature_c}°C
          </div>
        </div>
      )}

      {/* Primary KPI Grid with count-up animations */}
      <div ref={metricsRef} className="grid grid-cols-2 gap-2.5">
        <div data-metric className="metric-card bg-dark-800/80 p-3 rounded-xl border border-white/5">
          <AnimatedMetric
            value={summary.total_estimated_capacity_kw}
            className="text-xl font-bold text-solar-400"
            suffix=" kW"
          />
          <span className="metric-label text-[11px] text-dark-300 mt-0.5">
            Total Solar Capacity
          </span>
        </div>
        <div data-metric className="metric-card bg-dark-800/80 p-3 rounded-xl border border-white/5">
          <AnimatedMetric
            value={summary.total_estimated_annual_energy_kwh / 1000}
            decimals={1}
            className="text-xl font-bold text-emerald-400"
            suffix=" MWh"
          />
          <span className="metric-label text-[11px] text-dark-300 mt-0.5">
            Est. Annual Generation
          </span>
        </div>
        <div data-metric className="metric-card bg-dark-800/80 p-3 rounded-xl border border-white/5">
          <AnimatedMetric
            value={summary.total_usable_surface_area_m2}
            className="text-xl font-bold text-white"
            suffix=" m²"
          />
          <span className="metric-label text-[11px] text-dark-300 mt-0.5">
            Total Usable Area
          </span>
        </div>
        <div data-metric className="metric-card bg-dark-800/80 p-3 rounded-xl border border-white/5">
          <AnimatedMetric
            value={summary.average_solar_score}
            decimals={2}
            className="text-xl font-bold text-amber-400"
          />
          <span className="metric-label text-[11px] text-dark-300 mt-0.5">
            Avg Suitability Score
          </span>
        </div>
      </div>

      {/* Suitability Distribution Bar */}
      <div data-metric className="bg-dark-800/80 p-3 rounded-xl border border-white/5 space-y-1.5">
        <div className="flex justify-between text-xs text-dark-200">
          <span>Building Potential Breakdown</span>
          <span className="text-[11px] text-dark-300">
            {summary.high_potential_count} High · {summary.medium_potential_count} Med · {summary.low_potential_count} Low
          </span>
        </div>
        <div className="h-2.5 bg-dark-900 rounded-full flex overflow-hidden">
          <div
            className="bg-emerald-500 transition-all duration-700 ease-out"
            style={{
              width: `${(summary.high_potential_count / max1(summary.building_count)) * 100}%`,
            }}
            title="High Potential"
          />
          <div
            className="bg-amber-500 transition-all duration-700 ease-out"
            style={{
              width: `${(summary.medium_potential_count / max1(summary.building_count)) * 100}%`,
            }}
            title="Medium Potential"
          />
          <div
            className="bg-slate-500 transition-all duration-700 ease-out"
            style={{
              width: `${(summary.low_potential_count / max1(summary.building_count)) * 100}%`,
            }}
            title="Low Potential"
          />
        </div>
      </div>

      {/* Strategic Actions: AI & Capacity Optimizer */}
      <div data-metric className="grid grid-cols-2 gap-2 pt-1">
        <button
          onClick={onOpenAIExplainer}
          className="p-2.5 bg-gradient-to-r from-solar-500/20 to-amber-500/20 hover:from-solar-500/30 hover:to-amber-500/30 border border-solar-500/40 rounded-xl text-left transition-all group"
        >
          <div className="flex items-center gap-1.5 text-xs font-semibold text-solar-400">
            <span>✨</span>
            <span>Ask SolarIQ AI</span>
          </div>
          <p className="text-[10px] text-dark-300 mt-0.5">
            Grounded recommendations
          </p>
        </button>

        <button
          onClick={onOpenCapacityOptimizer}
          className="p-2.5 bg-dark-800 hover:bg-dark-700 border border-white/10 rounded-xl text-left transition-all group"
        >
          <div className="flex items-center gap-1.5 text-xs font-semibold text-white group-hover:text-solar-400">
            <span>🎯</span>
            <span>Budget / kW Limit</span>
          </div>
          <p className="text-[10px] text-dark-300 mt-0.5">
            Optimize target capacity
          </p>
        </button>
      </div>

      {/* Tabs: Ranked Buildings vs Ranked Surfaces */}
      <div className="flex border-b border-white/10 text-xs">
        <button
          onClick={() => setActiveTab("buildings")}
          className={`pb-2 px-3 font-semibold transition-colors border-b-2 ${
            activeTab === "buildings"
              ? "border-solar-500 text-solar-400"
              : "border-transparent text-dark-400 hover:text-white"
          }`}
        >
          Buildings ({data.buildings.length})
        </button>
        <button
          onClick={() => setActiveTab("surfaces")}
          className={`pb-2 px-3 font-semibold transition-colors border-b-2 ${
            activeTab === "surfaces"
              ? "border-solar-500 text-solar-400"
              : "border-transparent text-dark-400 hover:text-white"
          }`}
        >
          Ranked Surfaces ({data.ranked_surfaces.length})
        </button>
      </div>

      {/* Tab Content: Buildings List */}
      {activeTab === "buildings" && (
        <div ref={listRef} className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
          {data.buildings.map((b) => (
            <button
              key={b.building_id}
              data-list-item
              onClick={() => onSelectBuilding(b)}
              className="w-full glass-panel-solid p-3 rounded-xl text-left hover:bg-dark-700/80 transition-all border border-white/5 hover:border-solar-500/30 group"
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs font-semibold text-white group-hover:text-solar-400 transition-colors flex items-center gap-1.5">
                    <span>{b.name || b.building_id}</span>
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                        b.solar_suitability === "high"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : b.solar_suitability === "medium"
                          ? "bg-amber-500/20 text-amber-300"
                          : "bg-slate-500/20 text-slate-300"
                      }`}
                    >
                      {b.solar_suitability.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[10px] text-dark-300 mt-1">
                    {b.surface_count} surfaces · {b.height_m.toFixed(1)}m height
                    {b.height_estimated && " (est.)"}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold text-solar-400">
                    {b.estimated_capacity_kw.toFixed(1)} kW
                  </div>
                  <div className="text-[10px] text-dark-300">
                    {b.estimated_annual_energy_kwh.toFixed(0)} kWh/yr
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Tab Content: Ranked Surfaces List */}
      {activeTab === "surfaces" && (
        <div ref={listRef} className="space-y-2 max-h-[380px] overflow-y-auto pr-1">
          {data.ranked_surfaces.map((s) => (
            <div
              key={s.surface_id}
              data-list-item
              className="glass-panel-solid p-3 rounded-xl border border-white/5 space-y-1.5 text-xs"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-5 h-5 rounded-full bg-solar-500/20 text-solar-400 font-bold text-[10px] flex items-center justify-center">
                    #{s.rank}
                  </span>
                  <span className="font-semibold text-white">
                    {s.building_id} · {s.surface_type.toUpperCase()}
                  </span>
                </div>
                <span className="text-xs font-bold text-solar-400">
                  {s.estimated_capacity_kw.toFixed(1)} kW
                </span>
              </div>
              <p className="text-[10px] text-dark-300">
                {s.recommendation}
              </p>
              <div className="flex items-center justify-between text-[10px] text-dark-400 pt-1 border-t border-white/5">
                <span>Azimuth: {s.azimuth_deg}° · Tilt: {s.tilt_deg}°</span>
                <span className="font-mono text-emerald-400">
                  {s.estimated_annual_energy_kwh.toLocaleString()} kWh/yr
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function max1(n: number) {
  return Math.max(1, n);
}
