import { useEffect, useRef } from "react";
import { staggerFadeIn } from "../lib/animations";
import { animate } from "animejs";

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function HeroScreen({
  onStart,
  error,
}: {
  onStart: () => void;
  error: string | null;
}) {
  const contentRef = useRef<HTMLDivElement>(null);
  const sunRef = useRef<SVGSVGElement>(null);
  const diamondOuterRef = useRef<HTMLDivElement>(null);
  const diamondInnerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!contentRef.current) return;

    const el = contentRef.current;
    const cleanups: (() => void)[] = [];

    // Stagger fade in all [data-anim] children
    cleanups.push(
      staggerFadeIn(Array.from(el.querySelectorAll("[data-anim]")) as HTMLElement[], {
        duration: 500,
        staggerDelay: 70,
        startDelay: 100,
      })
    );

    // Subtle sun icon rotation — very slow, cinematic
    if (sunRef.current && !prefersReducedMotion()) {
      const sunAnim = animate(sunRef.current, {
        rotate: [0, 360],
        duration: 60000,
        ease: "linear",
        repeat: -1,
      });
      cleanups.push(() => sunAnim.cancel());
    }

    // Gentle diamond border pulse — scale breathe
    if (diamondOuterRef.current && !prefersReducedMotion()) {
      const outerAnim = animate(diamondOuterRef.current, {
        scale: [1, 1.04, 1],
        opacity: [0.2, 0.35, 0.2],
        duration: 4000,
        ease: "inOutSine",
        repeat: -1,
      });
      cleanups.push(() => outerAnim.cancel());
    }

    if (diamondInnerRef.current && !prefersReducedMotion()) {
      const innerAnim = animate(diamondInnerRef.current, {
        scale: [1, 1.06, 1],
        opacity: [0.1, 0.22, 0.1],
        duration: 5000,
        ease: "inOutSine",
        repeat: -1,
      });
      cleanups.push(() => innerAnim.cancel());
    }

    return () => cleanups.forEach((fn) => fn());
  }, []);

  return (
    <div className="h-full flex flex-col items-center justify-center bg-dark-950 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-solar-600/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-solar-600/20 to-transparent" />
      </div>

      {/* Content */}
      <div ref={contentRef} className="relative z-10 text-center max-w-2xl px-6">
        {/* Logo */}
        <div data-anim className="mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 mb-6 relative">
            <div ref={diamondOuterRef} className="absolute inset-0 border-2 border-solar-500/20 rounded-2xl rotate-45" />
            <div ref={diamondInnerRef} className="absolute inset-2 border border-solar-500/10 rounded-xl rotate-45" />
            <svg ref={sunRef} className="w-10 h-10 text-solar-500 relative z-10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="5" />
              <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
            </svg>
          </div>
        </div>

        <h1 data-anim className="text-5xl md:text-6xl font-bold tracking-tight">
          <span className="text-white">SOLAR</span>
          <span className="text-gradient-solar">IQ</span>
        </h1>

        <p data-anim className="text-lg text-dark-200 mt-4 tracking-wider uppercase font-light">
          AI-Powered Solar Intelligence
        </p>

        <p data-anim className="text-sm text-dark-300 mt-2">
          Building Integrated Photovoltaic Potential Assessment
        </p>

        {/* Start button */}
        <div data-anim className="mt-10">
          <button
            onClick={onStart}
            className="btn-primary text-base px-8 py-3 glow-solar"
          >
            Begin Analysis
          </button>
        </div>

        {error && (
          <p data-anim className="mt-4 text-sm text-red-400">
            {error}
          </p>
        )}

        {/* Feature badges */}
        <div data-anim className="mt-12 flex flex-wrap justify-center gap-3">
          {[
            "3D Building Analysis",
            "Surface Classification",
            "Solar Scoring",
            "Energy Estimation",
            "AI Recommendations",
          ].map((feature) => (
            <span
              key={feature}
              className="px-3 py-1.5 text-xs text-dark-300 bg-dark-800 border border-white/5 rounded-full"
            >
              {feature}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
