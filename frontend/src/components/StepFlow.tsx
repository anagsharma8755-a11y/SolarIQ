import type { AnalysisStep } from "../lib/types";

const STEPS: { id: AnalysisStep; label: string; num: number }[] = [
  { id: "select-building", label: "Select Building", num: 1 },
  { id: "analyze-surfaces", label: "Analyze Surfaces", num: 2 },
  { id: "solar-potential", label: "Solar Potential", num: 3 },
  { id: "energy-estimation", label: "Energy Estimation", num: 4 },
  { id: "recommendation", label: "Recommendation", num: 5 },
];

export function StepFlow({ currentStep }: { currentStep: AnalysisStep }) {
  const currentIdx = STEPS.findIndex((s) => s.id === currentStep);

  return (
    <div className="pointer-events-auto">
      <div className="glass-panel px-4 py-3 inline-flex items-center gap-3">
        {STEPS.map((step, i) => {
          const isComplete = i < currentIdx;
          const isActive = i === currentIdx;
          return (
            <div key={step.id} className="flex items-center gap-2">
              <div
                className={`step-indicator ${
                  isComplete
                    ? "step-complete"
                    : isActive
                    ? "step-active"
                    : "step-pending"
                }`}
              >
                {isComplete ? "✓" : step.num}
              </div>
              <span
                className={`text-xs hidden md:inline ${
                  isActive ? "text-solar-400" : isComplete ? "text-green-400" : "text-dark-400"
                }`}
              >
                {step.label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className={`w-6 h-px ${
                    i < currentIdx ? "bg-green-500/50" : "bg-dark-600"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
