import { useState, useEffect, useRef } from "react";
import { api } from "../lib/api";
import type { LocationSearchResult } from "../lib/types";

interface LocationSearchBarProps {
  onSelectLocation: (loc: LocationSearchResult, radiusM: number) => void;
  onRadiusChange: (radiusM: number) => void;
  radiusMeters: number;
  analyzing: boolean;
  viewMode: "map" | "3d";
  onToggleViewMode: (mode: "map" | "3d") => void;
}

export function LocationSearchBar({
  onSelectLocation,
  onRadiusChange,
  radiusMeters,
  analyzing,
  viewMode,
  onToggleViewMode,
}: LocationSearchBarProps) {
  const [query, setQuery] = useState("Bandra West, Mumbai");
  const [results, setResults] = useState<LocationSearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [selectedLoc, setSelectedLoc] = useState<LocationSearchResult | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch initial curated sample locations
  useEffect(() => {
    async function loadSamples() {
      try {
        const samples = await api.getSampleAreas();
        setResults(samples);
        if (samples.length > 0 && !selectedLoc) {
          setSelectedLoc(samples[0]);
        }
      } catch (err) {
        console.warn("Failed to load sample areas:", err);
      }
    }
    loadSamples();
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSearchChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);

    if (val.trim().length >= 2) {
      setLoadingSuggestions(true);
      try {
        const res = await api.searchLocations(val, 6);
        setResults(res);
        setShowDropdown(true);
      } catch (err) {
        console.error("Geocoding failed:", err);
      } finally {
        setLoadingSuggestions(false);
      }
    } else {
      setShowDropdown(false);
    }
  };

  const handleSelectResult = (loc: LocationSearchResult) => {
    setQuery(loc.display_name.split(",").slice(0, 2).join(", "));
    setSelectedLoc(loc);
    setShowDropdown(false);
    onSelectLocation(loc, radiusMeters);
  };

  const handleAnalyzeClick = () => {
    if (selectedLoc) {
      onSelectLocation(selectedLoc, radiusMeters);
    } else {
      // Fallback
      onSelectLocation(
        {
          location_name: query,
          display_name: query,
          latitude: 19.0596,
          longitude: 72.8295,
          bounding_box: [19.045, 72.815, 19.075, 72.845],
          category: "suburb",
          importance: 0.85,
          is_demo: true,
        },
        radiusMeters
      );
    }
  };

  return (
    <div
      ref={containerRef}
      className="glass-panel-solid p-2.5 rounded-xl flex flex-wrap items-center gap-2 shadow-2xl border border-white/10"
    >
      {/* Search Input Box */}
      <div className="relative flex-1 min-w-[240px]">
        <div className="relative flex items-center">
          <span className="absolute left-3 text-dark-300">🔍</span>
          <input
            type="text"
            value={query}
            onChange={handleSearchChange}
            onFocus={() => setShowDropdown(results.length > 0)}
            placeholder="Search real location (e.g. Bandra West, Mumbai)..."
            className="w-full bg-dark-800/90 text-white text-sm pl-9 pr-8 py-2 rounded-lg border border-white/10 focus:border-solar-500 focus:outline-none placeholder-dark-400"
          />
          {loadingSuggestions && (
            <div className="absolute right-3 w-4 h-4 border-2 border-solar-500 border-t-transparent rounded-full animate-spin" />
          )}
        </div>

        {/* Dropdown Menu */}
        {showDropdown && results.length > 0 && (
          <div className="absolute left-0 right-0 top-full mt-1.5 bg-dark-900/95 border border-white/10 rounded-lg shadow-2xl z-50 max-h-64 overflow-y-auto backdrop-blur-xl">
            <div className="p-1.5 text-[10px] font-semibold text-dark-400 uppercase tracking-wider px-3">
              Locations & Landmarks
            </div>
            {results.map((loc, idx) => (
              <button
                key={idx}
                onClick={() => handleSelectResult(loc)}
                className="w-full text-left px-3 py-2 text-xs text-dark-100 hover:bg-solar-500/20 hover:text-white transition-colors flex items-center justify-between border-b border-white/5 last:border-0"
              >
                <div className="truncate pr-2">
                  <div className="font-medium text-white">{loc.location_name}</div>
                  <div className="text-[10px] text-dark-300 truncate">
                    {loc.display_name}
                  </div>
                </div>
                {loc.is_demo && (
                  <span className="text-[9px] font-mono bg-solar-500/20 text-solar-400 px-1.5 py-0.5 rounded flex-shrink-0">
                    DEMO
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Radius Dropdown */}
      <div className="flex items-center gap-1.5 bg-dark-800/90 px-2.5 py-1.5 rounded-lg border border-white/10 text-xs text-dark-200">
        <span>Radius:</span>
        <select
          value={radiusMeters}
          onChange={(e) => {
            const r = Number(e.target.value);
            onRadiusChange(r);
          }}
          className="bg-transparent text-white font-medium focus:outline-none cursor-pointer"
        >
          <option value={200} className="bg-dark-900">200 m</option>
          <option value={400} className="bg-dark-900">400 m</option>
          <option value={800} className="bg-dark-900">800 m</option>
          <option value={1500} className="bg-dark-900">1500 m</option>
        </select>
      </div>

      {/* Primary Action: Analyze Area */}
      <button
        onClick={handleAnalyzeClick}
        disabled={analyzing}
        className="px-4 py-2 bg-gradient-to-r from-solar-500 to-amber-500 hover:from-solar-600 hover:to-amber-600 text-dark-950 font-semibold text-xs rounded-lg transition-all shadow-md shadow-solar-500/20 flex items-center gap-2 disabled:opacity-50"
      >
        {analyzing ? (
          <>
            <div className="w-3.5 h-3.5 border-2 border-dark-950 border-t-transparent rounded-full animate-spin" />
            <span>Analyzing...</span>
          </>
        ) : (
          <>
            <span>⚡ Analyze Area</span>
          </>
        )}
      </button>

      {/* View Switcher: Map vs 3D */}
      <div className="flex items-center bg-dark-800/90 rounded-lg p-0.5 border border-white/10">
        <button
          onClick={() => onToggleViewMode("map")}
          className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
            viewMode === "map"
              ? "bg-solar-500 text-dark-950 shadow"
              : "text-dark-300 hover:text-white"
          }`}
        >
          🗺️ GIS Map
        </button>
        <button
          onClick={() => onToggleViewMode("3d")}
          className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
            viewMode === "3d"
              ? "bg-solar-500 text-dark-950 shadow"
              : "text-dark-300 hover:text-white"
          }`}
        >
          🏢 3D Mesh
        </button>
      </div>
    </div>
  );
}
