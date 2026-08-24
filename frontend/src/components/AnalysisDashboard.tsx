import type { BuildingAnalysisResponse, OptimizationResponse } from "../lib/types";

export function AnalysisDashboard({
  building,
  optimization,
  visible,
  onRunOptimization,
}: {
  building: BuildingAnalysisResponse;
  optimization: OptimizationResponse | null;
  visible: boolean;
  onRunOptimization: () => void;
}) {
  if (!visible) return null;

  const totalCapacity = building.estimated_capacity_kw;
  const totalEnergy = building.estimated_annual_energy_kwh;
  const co2Reduction = totalEnergy * 0.00075;

  // Best surface
  const bestSurface = [...building.surfaces].sort(
    (a, b) => b.solar_score - a.solar_score
  )[0];

  return (
    <div className="absolute bottom-20 left-4 right-4 z-10 pointer-events-none">
      <div className="glass-panel p-4 max-w-3xl mx-auto pointer-events-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Solar Potential */}
          <div className="text-center">
            <div className="text-3xl font-bold text-solar-400">
              {bestSurface
                ? (bestSurface.solar_score * 100).toFixed(0)
                : "--"}
              %
            </div>
            <div className="text-[10px] text-dark-300 uppercase tracking-wider mt-1">
              Solar Potential
            </div>
          </div>

          {/* Roof Area */}
          <div className="text-center">
            <div className="text-3xl font-bold text-white">
              {building.surfaces
                .filter((s) => s.surface_type === "roof")
                .reduce((sum, s) => sum + s.area_m2, 0)
                .toFixed(0)}
            </div>
            <div className="text-[10px] text-dark-300 uppercase tracking-wider mt-1">
              Roof Area (m²)
            </div>
          </div>

          {/* Estimated Capacity */}
          <div className="text-center">
            <div className="text-3xl font-bold text-white">
              {totalCapacity.toFixed(1)}
            </div>
            <div className="text-[10px] text-dark-300 uppercase tracking-wider mt-1">
              Capacity (kWp)
            </div>
          </div>

          {/* Annual Generation */}
          <div className="text-center">
            <div className="text-3xl font-bold text-white">
              {(totalEnergy / 1000).toFixed(1)}
            </div>
            <div className="text-[10px] text-dark-300 uppercase tracking-wider mt-1">
              Generation (MWh/yr)
            </div>
          </div>
        </div>

        {/* Secondary metrics */}
        <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-white/5">
          <div className="text-center">
            <div className="text-lg font-semibold text-green-400">
              {co2Reduction.toFixed(0)} t
            </div>
            <div className="text-[9px] text-dark-400">CO₂ Reduction/yr</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-white">
              {building.surfaces.length}
            </div>
            <div className="text-[9px] text-dark-400">Surfaces Analyzed</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-semibold text-white">
              {building.usable_surface_area_m2.toFixed(0)} m²
            </div>
            <div className="text-[9px] text-dark-400">Usable Area</div>
          </div>
        </div>
      </div>
    </div>
  );
}
