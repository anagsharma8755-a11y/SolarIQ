import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import type { BuildingAnalysisResponse, OptimizationResponse } from "../lib/types";

const SUITABILITY_COLORS: Record<string, string> = {
  excellent: "#4CAF50",
  high: "#66BB6A",
  moderate: "#FFC107",
  low: "#FF9800",
  poor: "#F44336",
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-panel px-3 py-2 text-xs">
      <div className="text-white font-medium">{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} className="text-dark-300 mt-0.5">
          {p.name}: {typeof p.value === "number" ? p.value.toFixed(1) : p.value}
        </div>
      ))}
    </div>
  );
}

export default function AnalysisCharts({
  building,
  optimization,
  visible,
}: {
  building: BuildingAnalysisResponse;
  optimization: OptimizationResponse | null;
  visible: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!visible) return null;

  // Surface data for bar chart
  const surfaceData = building.surfaces.map((s) => ({
    id: s.surface_id.replace(/^.*-/, ""),
    score: +(s.solar_score * 100).toFixed(0),
    area: +s.area_m2.toFixed(0),
    capacity: +s.energy_potential.estimated_capacity_kw.toFixed(1),
    type: s.surface_type,
  }));

  // Surface type distribution
  const typeCounts: Record<string, number> = {};
  building.surfaces.forEach((s) => {
    typeCounts[s.surface_type] = (typeCounts[s.surface_type] || 0) + 1;
  });
  const pieData = Object.entries(typeCounts).map(([name, value]) => ({
    name,
    value,
  }));

  // Suitability distribution
  const suitCounts: Record<string, number> = {};
  building.surfaces.forEach((s) => {
    suitCounts[s.solar_suitability] = (suitCounts[s.solar_suitability] || 0) + 1;
  });

  return (
    <div className="absolute top-16 right-[396px] z-10 pointer-events-auto">
      {/* Toggle button */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="glass-panel px-3 py-1.5 text-[10px] text-dark-200 hover:text-white transition-colors mb-1"
      >
        {expanded ? "Hide Charts" : "Show Charts"} ▾
      </button>

      {expanded && (
        <div className="glass-panel p-4 w-[320px] space-y-4">
          <h3 className="text-xs font-medium text-dark-200 uppercase tracking-wider">
            Solar Score Distribution
          </h3>

          {/* Bar chart */}
          <div className="h-[160px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={surfaceData}>
                <XAxis
                  dataKey="id"
                  tick={{ fill: "#5f6368", fontSize: 10 }}
                  axisLine={{ stroke: "#2d2e31" }}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: "#5f6368", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={30}
                />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="score" name="Score" radius={[2, 2, 0, 0]}>
                  {surfaceData.map((entry) => (
                    <Cell
                      key={entry.id}
                      fill={
                        entry.score >= 80
                          ? "#4CAF50"
                          : entry.score >= 60
                          ? "#66BB6A"
                          : entry.score >= 40
                          ? "#FFC107"
                          : "#FF9800"
                      }
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Pie charts row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-[10px] text-dark-400 mb-1">By Type</h4>
              <div className="h-[100px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={20}
                      outerRadius={35}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {pieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={
                            entry.name === "roof"
                              ? "#FFB300"
                              : entry.name === "facade"
                              ? "#42A5F5"
                              : "#78909C"
                          }
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-3 mt-1">
                {pieData.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-1">
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{
                        backgroundColor:
                          entry.name === "roof"
                            ? "#FFB300"
                            : entry.name === "facade"
                            ? "#42A5F5"
                            : "#78909C",
                      }}
                    />
                    <span className="text-[9px] text-dark-400 capitalize">
                      {entry.name}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-[10px] text-dark-400 mb-1">By Suitability</h4>
              <div className="space-y-1.5 mt-2">
                {Object.entries(suitCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([label, count]) => (
                    <div key={label} className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{
                          backgroundColor: SUITABILITY_COLORS[label] || "#9E9E9E",
                        }}
                      />
                      <span className="text-[10px] text-dark-300 capitalize flex-1">
                        {label}
                      </span>
                      <span className="text-[10px] text-white font-medium">
                        {count}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
