import { useState, useRef, useEffect } from "react";
import { api } from "../lib/api";
import type { AreaAnalysisResponse, AIExplanationResponse } from "../lib/types";
import { staggerFadeIn, slideInUp } from "../lib/animations";

interface AIExplainerPanelProps {
  areaData: AreaAnalysisResponse;
  onClose: () => void;
  onOptimizeCapacity?: (targetKw: number) => void;
}

const PRESET_QUESTIONS = [
  "Where should I install solar panels in this area?",
  "Which buildings are best for solar?",
  "What if I only have 500 kW available?",
  "Which surfaces should be avoided?",
];

export function AIExplainerPanel({
  areaData,
  onClose,
  onOptimizeCapacity,
}: AIExplainerPanelProps) {
  const [query, setQuery] = useState("");
  const [explanation, setExplanation] = useState<AIExplanationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const handleAsk = async (questionText: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.explainAI({
        analysis_id: areaData.analysis_id,
        query: questionText,
        analysis_data: areaData,
      });
      setExplanation(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI explanation failed");
    } finally {
      setLoading(false);
    }
  };

  // Animate results reveal when explanation changes
  useEffect(() => {
    if (!explanation || !resultsRef.current) return;
    const cleanup = staggerFadeIn(
      Array.from(resultsRef.current.querySelectorAll("[data-reveal]")) as HTMLElement[],
      { duration: 400, staggerDelay: 60, startDelay: 50 }
    );
    return cleanup;
  }, [explanation]);

  return (
    <div className="glass-panel-solid rounded-2xl p-5 border border-white/10 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-solar-500/20 border border-solar-500/30 flex items-center justify-center text-solar-400 font-bold text-sm">
            AI
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">SolarIQ AI Strategic Explainer</h3>
            <p className="text-[11px] text-dark-300">
              Data-grounded architectural & BIPV deployment insights
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

      {/* Preset Quick Questions */}
      <div>
        <div className="text-[11px] font-semibold text-dark-300 uppercase tracking-wider mb-2">
          Suggested Inquiries
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {PRESET_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleAsk(q)}
              disabled={loading}
              className="text-left text-xs bg-dark-800/80 hover:bg-solar-500/20 text-dark-100 hover:text-white p-2.5 rounded-lg border border-white/5 transition-all flex items-start gap-1.5 group"
            >
              <span className="text-solar-400 mt-0.5 text-[10px]">✨</span>
              <span className="line-clamp-2">{q}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Question Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && query.trim() && handleAsk(query)}
          placeholder="Ask anything about this area's solar potential..."
          className="flex-1 bg-dark-800 text-white text-xs px-3 py-2.5 rounded-lg border border-white/10 focus:border-solar-500 focus:outline-none placeholder-dark-400"
        />
        <button
          onClick={() => query.trim() && handleAsk(query)}
          disabled={loading || !query.trim()}
          className="px-4 py-2.5 bg-solar-500 hover:bg-solar-600 text-dark-950 font-semibold text-xs rounded-lg transition-all disabled:opacity-50 flex items-center gap-1.5"
        >
          {loading ? (
            <div className="w-3.5 h-3.5 border-2 border-dark-950 border-t-transparent rounded-full animate-spin" />
          ) : (
            <span>Ask</span>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Loading shimmer */}
      {loading && (
        <div className="space-y-3 pt-2">
          <div className="h-20 bg-dark-800/50 rounded-xl animate-pulse" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-32 bg-dark-800/50 rounded-xl animate-pulse" />
            <div className="h-32 bg-dark-800/50 rounded-xl animate-pulse" />
          </div>
        </div>
      )}

      {/* Results View */}
      {explanation && !loading && (
        <div ref={resultsRef} className="space-y-4 pt-2">
          {/* Headline */}
          <div data-reveal className="p-3 bg-solar-500/10 border border-solar-500/20 rounded-xl">
            <h4 className="text-sm font-semibold text-solar-400">
              {explanation.headline}
            </h4>
            <p className="text-xs text-dark-100 mt-1 leading-relaxed">
              {explanation.ai_interpretation.summary}
            </p>
          </div>

          {/* Explicit Separation: Calculated Facts vs Interpretation */}
          <div data-reveal className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* CALCULATED RESULTS (Hard Physics Data) */}
            <div className="bg-dark-900/90 p-3.5 rounded-xl border border-white/10 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                <span>📐</span>
                <span>Calculated Results (Exact Data)</span>
              </div>
              <ul className="text-[11px] text-dark-200 space-y-1.5 list-disc list-inside">
                {explanation.calculated_results.map((fact, idx) => (
                  <li key={idx} className="leading-snug">
                    {fact}
                  </li>
                ))}
              </ul>
            </div>

            {/* AI STRATEGIC INTERPRETATION */}
            <div className="bg-dark-900/90 p-3.5 rounded-xl border border-white/10 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
                <span>💡</span>
                <span>AI Strategic Recommendations</span>
              </div>
              <ul className="text-[11px] text-dark-200 space-y-1.5 list-disc list-inside">
                {explanation.ai_interpretation.recommendations.map((rec, idx) => (
                  <li key={idx} className="leading-snug">
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Phased Rollout Plan if optimization context present */}
          {explanation.optimization_context?.phases && (
            <div data-reveal className="bg-dark-900/90 p-3.5 rounded-xl border border-white/10 space-y-2.5">
              <div className="text-xs font-semibold text-white flex items-center justify-between">
                <span>Recommended Phased Deployment</span>
                <span className="text-[11px] text-solar-400 font-mono">
                  {explanation.optimization_context.selected_capacity_kw.toFixed(1)} kW Target
                </span>
              </div>
              <div className="space-y-2">
                {explanation.optimization_context.phases.map((phase) => (
                  <div
                    key={phase.phase}
                    className="p-2.5 bg-dark-800/80 rounded-lg border border-white/5 flex items-start justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="font-semibold text-dark-100">
                        Phase {phase.phase}: {phase.name}
                      </div>
                      <div className="text-[11px] text-dark-300 mt-0.5">
                        {phase.description}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="font-medium text-solar-400">
                        {phase.capacity_kw} kW
                      </div>
                      <div className="text-[10px] text-dark-300">
                        {(phase.annual_energy_kwh / 1000).toFixed(1)} MWh/yr
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Avoidance Guidelines & Disclaimer */}
          <div data-reveal className="text-[10px] text-dark-400 space-y-1 border-t border-white/10 pt-2.5">
            <div>
              <strong className="text-dark-300">Avoidance Notes: </strong>
              {explanation.ai_interpretation.avoidance_guidelines}
            </div>
            <div>
              <strong className="text-dark-300">Provenance: </strong>
              {explanation.ai_interpretation.disclaimer}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
