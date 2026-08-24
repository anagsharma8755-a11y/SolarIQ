import { useEffect, useRef } from "react";
import { staggerFadeIn, pulseGlow } from "../lib/animations";

export function LoadingScreen() {
  const logoRef = useRef<HTMLDivElement>(null);
  const dotsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const cleanups: (() => void)[] = [];

    if (logoRef.current) {
      cleanups.push(
        staggerFadeIn(Array.from(logoRef.current.querySelectorAll("[data-anim]")) as HTMLElement[], {
          duration: 500,
          staggerDelay: 80,
        })
      );
    }

    if (dotsRef.current) {
      const dots = Array.from(dotsRef.current.querySelectorAll("[data-dot]")) as HTMLElement[];
      dots.forEach((dot) => {
        cleanups.push(pulseGlow(dot, { duration: 1800 }));
      });
      cleanups.push(
        staggerFadeIn(Array.from(dotsRef.current.querySelectorAll("[data-step]")) as HTMLElement[], {
          duration: 400,
          staggerDelay: 200,
          startDelay: 300,
        })
      );
    }

    return () => cleanups.forEach((fn) => fn());
  }, []);

  return (
    <div className="h-full flex flex-col items-center justify-center bg-dark-950">
      <div className="flex flex-col items-center gap-6">
        {/* Logo mark */}
        <div ref={logoRef} className="relative">
          <div data-anim className="w-16 h-16 border-2 border-solar-500/30 rounded-xl rotate-45" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div data-anim data-dot className="w-8 h-8 bg-solar-500 rounded-lg animate-pulse-glow" />
          </div>
        </div>

        {/* Text */}
        <div ref={dotsRef} className="text-center">
          <h1 data-anim className="text-2xl font-bold tracking-wider text-white">
            SOLAR<span className="text-gradient-solar">IQ</span>
          </h1>
          <p data-anim className="text-xs text-dark-300 tracking-widest mt-2 uppercase">
            Initializing Solar Intelligence
          </p>

          {/* Loading steps */}
          <div className="flex flex-col items-center gap-2 mt-4">
            {["Building Model", "Solar Data", "Surface Analysis"].map((label, i) => (
              <div
                key={label}
                data-step
                className="flex items-center gap-2 text-xs"
                style={{ animationDelay: `${i * 400}ms` }}
              >
                <div
                  data-dot
                  className="w-1.5 h-1.5 rounded-full bg-solar-500"
                  style={{ animationDelay: `${i * 400}ms` }}
                />
                <span className="text-dark-300">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
