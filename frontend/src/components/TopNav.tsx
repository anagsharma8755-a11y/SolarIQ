import type { AppView } from "../lib/types";

const NAV_ITEMS: { label: string; view: AppView }[] = [
  { label: "🗺️ GIS City Map", view: "map" },
  { label: "🏢 City 3D", view: "city" },
  { label: "📐 Building Analysis", view: "building" },
  { label: "⚡ Solar Potential", view: "building" },
  { label: "🎯 Recommendations", view: "building" },
];

export function TopNav({
  view,
  onHome,
  onNavigate,
}: {
  view: AppView;
  onHome: () => void;
  onNavigate: (v: AppView) => void;
}) {
  return (
    <nav className="h-12 bg-dark-900/80 backdrop-blur-xl border-b border-white/5 flex items-center px-4 gap-6 flex-shrink-0 z-20">
      {/* Logo */}
      <button
        onClick={onHome}
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <div className="w-6 h-6 bg-solar-500 rounded-md flex items-center justify-center">
          <svg className="w-3.5 h-3.5 text-dark-900" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="12" r="5" />
          </svg>
        </div>
        <span className="text-sm font-bold tracking-wide">
          <span className="text-white">SOLAR</span>
          <span className="text-solar-500">IQ</span>
        </span>
      </button>

      {/* Divider */}
      <div className="w-px h-5 bg-white/10" />

      {/* Nav items */}
      <div className="flex items-center gap-1">
        {NAV_ITEMS.map(({ label, view: v }) => (
          <button
            key={label}
            onClick={() => onNavigate(v)}
            className={`px-3 py-1.5 text-xs font-medium rounded transition-all duration-200 ${
              view === v
                ? "text-solar-400 bg-solar-500/10 shadow-sm shadow-solar-500/10"
                : "text-dark-300 hover:text-white hover:bg-white/5"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Status indicator */}
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-[10px] text-dark-300 uppercase tracking-wider">
          LIVE ENGINE
        </span>
      </div>
    </nav>
  );
}
