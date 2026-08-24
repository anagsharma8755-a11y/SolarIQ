import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AnalyzedSurface, SolarPredictionResponse } from "../lib/types";

function MetricRow({
  label,
  value,
  unit,
  color = "text-white",
}: {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-white/5 last:border-0">
      <span className="text-xs text-dark-300">{label}</span>
      <span className={`text-sm font-medium ${color}`}>
        {value}
        {unit && <span className="text-dark-400 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export function SurfaceDetailPanel({
  surface,
  onClose,
}: {
  surface: AnalyzedSurface;
  onClose: () => void;
}) {
  const [prediction, setPrediction] = useState<SolarPredictionResponse | null>(null);
  const [loadingPrediction, setLoadingPrediction] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function fetchPrediction() {
      setLoadingPrediction(true);
      try {
        const result = await api.predictSolar({
          surface_id: surface.surface_id,
          building_id: surface.building_id,
          area_m2: surface.area_m2,
          azimuth_deg: surface.azimuth_deg,
          tilt_deg: surface.tilt_deg,
          surface_type: surface.surface_type,
        });
        if (!cancelled) setPrediction(result);
      } catch {
        // Silently handle prediction errors
      } finally {
        if (!cancelled) setLoadingPrediction(false);
      }
    }
    fetchPrediction();
    return () => { cancelled = true; };
  }, [surface]);

  const scoreColor =
    surface.solar_score >= 0.8
      ? "text-green-400"
      : surface.solar_score >= 0.6
      ? "text-green-300"
      : surface.solar_score >= 0.4
      ? "text-solar-400"
      : surface.solar_score >= 0.2
      ? "text-orange-400"
      : "text-red-400";

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div>
        <button
          onClick={onClose}
          className="text-xs text-dark-300 hover:text-white transition-colors mb-2"
        >
          ← Back to building
        </button>
        <div className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded-full"
            style={{
              backgroundColor:
                surface.surface_type === "roof"
                  ? "#FFB300"
                  : surface.surface_type === "facade"
                  ? "#42A5F5"
                  : "#78909C",
            }}
          />
          <h2 className="text-lg font-semibold text-white uppercase">
            {surface.surface_type}
          </h2>
        </div>
        <div className="text-xs text-dark-400 font-mono mt-1">
          {surface.surface_id}
        </div>
      </div>

      {/* Solar Score */}
      <div className="glass-panel p-4 text-center glow-solar">
        <div className={`text-4xl font-bold ${scoreColor}`}>
          {(surface.solar_score * 100).toFixed(0)}%
        </div>
        <div className="text-xs text-dark-300 mt-1 uppercase tracking-wider">
          Solar Suitability
        </div>
        <div
          className="mt-2 text-sm font-medium capitalize"
          style={{
            color:
              surface.solar_score >= 0.8
                ? "#4CAF50"
                : surface.solar_score >= 0.6
                ? "#66BB6A"
                : surface.solar_score >= 0.4
                ? "#FFC107"
                : "#FF9800",
          }}
        >
          {surface.solar_suitability}
        </div>
      </div>

      {/* Geometry metrics */}
      <div className="glass-panel p-3">
        <h3 className="text-xs font-medium text-dark-200 uppercase tracking-wider mb-2">
          Geometry
        </h3>
        <MetricRow label="Area" value={surface.area_m2.toFixed(1)} unit="m²" />
        <MetricRow
          label="Azimuth"
          value={surface.azimuth_deg.toFixed(0)}
          unit="°"
        />
        <MetricRow
          label="Tilt"
          value={surface.tilt_deg.toFixed(0)}
          unit="°"
        />
        <MetricRow
          label="Normal"
          value={`(${surface.normal.x.toFixed(2)}, ${surface.normal.y.toFixed(2)}, ${surface.normal.z.toFixed(2)})`}
        />
      </div>

      {/* Energy Potential */}
      <div className="glass-panel p-3">
        <h3 className="text-xs font-medium text-dark-200 uppercase tracking-wider mb-2">
          Energy Potential
        </h3>
        <MetricRow
          label="Usable Area"
          value={surface.energy_potential.usable_area_m2.toFixed(1)}
          unit="m²"
          color="text-solar-400"
        />
        <MetricRow
          label="Est. Capacity"
          value={surface.energy_potential.estimated_capacity_kw.toFixed(1)}
          unit="kW"
          color="text-solar-400"
        />
        <MetricRow
          label="Annual Energy"
          value={surface.energy_potential.estimated_annual_energy_kwh.toFixed(0)}
          unit="kWh"
          color="text-solar-400"
        />
        <MetricRow
          label="CO₂ Reduction"
          value={(surface.energy_potential.estimated_annual_energy_kwh * 0.00075).toFixed(1)}
          unit="t/yr"
          color="text-green-400"
        />
      </div>

      {/* ML Prediction */}
      <div className="glass-panel p-3">
        <h3 className="text-xs font-medium text-dark-200 uppercase tracking-wider mb-2">
          ML Prediction
        </h3>
        {loadingPrediction ? (
          <div className="flex items-center gap-2 py-2">
            <div className="w-3 h-3 border border-solar-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-dark-300">Running prediction...</span>
          </div>
        ) : prediction ? (
          <div className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-dark-300">Model Status</span>
              <span className={prediction.available ? "text-green-400" : "text-dark-400"}>
                {prediction.available ? "Connected" : "Fallback"}
              </span>
            </div>
            <MetricRow
              label="Prediction Score"
              value={(prediction.fallback_score * 100).toFixed(0)}
              unit="%"
              color="text-solar-400"
            />
            <MetricRow
              label="Suitability"
              value={prediction.fallback_suitability}
              color="text-white capitalize"
            />
          </div>
        ) : (
          <div className="text-xs text-dark-400 py-2">No prediction available</div>
        )}
      </div>
    </div>
  );
}
