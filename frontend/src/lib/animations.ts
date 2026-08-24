/**
 * SolarIQ Animation Utilities — Anime.js v4 Micro-interactions
 *
 * Design Philosophy:
 *   TECHNICAL · CINEMATIC · PREVISE · FAST · PROFESSIONAL · MINIMAL
 *
 * All animations respect prefers-reduced-motion.
 * Cleanup functions are returned for React useEffect unmount.
 */

import { animate, stagger, type AnimationParams } from "animejs";

// ─── Reduced Motion Check ───

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function motionDuration(ms: number): number {
  return prefersReducedMotion() ? 0 : ms;
}

// ─── Cleanup Manager ───

type CleanupFn = () => void;

function noopCleanup(): CleanupFn {
  return () => {};
}

// ─── Fade In / Out ───

export function fadeIn(
  selector: string | HTMLElement | HTMLElement[],
  options?: Partial<AnimationParams>
): CleanupFn {
  if (prefersReducedMotion()) {
    const els = resolveElements(selector);
    els.forEach((el) => {
      (el as HTMLElement).style.opacity = "1";
    });
    return noopCleanup();
  }

  const anim = animate(selector, {
    opacity: [0, 1],
    duration: options?.duration ?? 300,
    delay: options?.delay ?? 0,
    ease: "outExpo",
    ...options,
  });
  return () => anim.cancel();
}

export function fadeOut(
  selector: string | HTMLElement | HTMLElement[],
  options?: Partial<AnimationParams>
): CleanupFn {
  if (prefersReducedMotion()) {
    return noopCleanup();
  }

  const anim = animate(selector, {
    opacity: [1, 0],
    duration: options?.duration ?? 250,
    delay: options?.delay ?? 0,
    ease: "inExpo",
    ...options,
  });
  return () => anim.cancel();
}

// ─── Slide In (from bottom) ───

export function slideInUp(
  selector: string | HTMLElement | HTMLElement[],
  options?: Partial<AnimationParams>
): CleanupFn {
  if (prefersReducedMotion()) {
    const els = resolveElements(selector);
    els.forEach((el) => {
      (el as HTMLElement).style.opacity = "1";
      (el as HTMLElement).style.transform = "translateY(0)";
    });
    return noopCleanup();
  }

  const anim = animate(selector, {
    translateY: [20, 0],
    opacity: [0, 1],
    duration: options?.duration ?? 400,
    delay: options?.delay ?? 0,
    ease: "outExpo",
    ...options,
  });
  return () => anim.cancel();
}

// ─── Staggered Fade In ───

export function staggerFadeIn(
  selector: string | HTMLElement[] | NodeListOf<Element>,
  options?: {
    duration?: number;
    staggerDelay?: number;
    startDelay?: number;
  }
): CleanupFn {
  const elements = toElementArray(selector);

  if (prefersReducedMotion() || elements.length === 0) {
    elements.forEach((el) => {
      (el as HTMLElement).style.opacity = "1";
    });
    return noopCleanup();
  }

  // Animate each element individually with staggered delay
  const fns: CleanupFn[] = [];
  const baseDelay = options?.startDelay ?? 0;
  const staggerDelay = options?.staggerDelay ?? 50;
  elements.forEach((el, i) => {
    const anim = animate(el as HTMLElement, {
      opacity: [0, 1],
      translateY: [12, 0],
      duration: options?.duration ?? 350,
      delay: baseDelay + i * staggerDelay,
      ease: "outExpo",
    });
    fns.push(() => anim.cancel());
  });
  return () => fns.forEach((fn) => fn());
}

// ─── Count Up (for metric values) ───

export function countUp(
  element: HTMLElement,
  target: number,
  options?: {
    duration?: number;
    decimals?: number;
    prefix?: string;
    suffix?: string;
  }
): CleanupFn {
  if (prefersReducedMotion()) {
    const formatted = formatNumber(target, options?.decimals ?? 0);
    element.textContent = `${options?.prefix ?? ""}${formatted}${options?.suffix ?? ""}`;
    return noopCleanup();
  }

  const decimals = options?.decimals ?? 0;
  const prefix = options?.prefix ?? "";
  const suffix = options?.suffix ?? "";

  const obj = { val: 0 };
  const anim = animate(obj, {
    val: target,
    duration: options?.duration ?? 1200,
    ease: "outExpo",
    onUpdate: () => {
      element.textContent = `${prefix}${formatNumber(obj.val, decimals)}${suffix}`;
    },
  });
  return () => anim.cancel();
}

// ─── Scan Line (analysis scanning effect) ───

export function scanLine(
  element: HTMLElement,
  options?: {
    duration?: number;
    color?: string;
  }
): CleanupFn {
  if (prefersReducedMotion()) return noopCleanup();

  // Create scan line element
  const line = document.createElement("div");
  line.style.cssText = `
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, ${options?.color ?? "#FFC107"}, transparent);
    opacity: 0;
    pointer-events: none;
    z-index: 50;
  `;
  element.style.position = element.style.position || "relative";
  element.appendChild(line);

  const anim = animate(line, {
    top: ["0%", "100%"],
    opacity: [0, 0.8, 0.8, 0],
    duration: options?.duration ?? 2000,
    ease: "linear",
    repeat: 3,
  });

  return () => {
    anim.cancel();
    line.remove();
  };
}

// ─── Pulse Glow ───

export function pulseGlow(
  selector: string | HTMLElement,
  options?: {
    duration?: number;
    scale?: [number, number];
  }
): CleanupFn {
  if (prefersReducedMotion()) return noopCleanup();

  const anim = animate(selector, {
    scale: options?.scale ?? [1, 1.05],
    opacity: [1, 0.7, 1],
    duration: options?.duration ?? 2000,
    ease: "inOutSine",
    repeat: -1,
  });
  return () => anim.cancel();
}

// ─── Panel Reveal ───

export function panelReveal(
  element: HTMLElement,
  options?: {
    direction?: "up" | "down" | "left" | "right";
    duration?: number;
  }
): CleanupFn {
  if (prefersReducedMotion()) {
    element.style.opacity = "1";
    element.style.transform = "translateY(0)";
    return noopCleanup();
  }

  const dir = options?.direction ?? "up";
  const translateMap: Record<string, [string, string]> = {
    up: ["24px", "0px"],
    down: ["-24px", "0px"],
    left: ["24px", "0px"],
    right: ["-24px", "0px"],
  };

  const [from, to] = translateMap[dir] ?? translateMap.up;
  const prop = dir === "left" || dir === "right" ? "translateX" : "translateY";

  const anim = animate(element, {
    [prop]: [from, to],
    opacity: [0, 1],
    duration: options?.duration ?? 450,
    ease: "outExpo",
  });
  return () => anim.cancel();
}

// ─── Utility: Resolve elements ───

function resolveElements(
  selector: string | HTMLElement | HTMLElement[]
): HTMLElement[] {
  if (typeof selector === "string") {
    return Array.from(document.querySelectorAll<HTMLElement>(selector));
  }
  if (Array.isArray(selector)) return selector as HTMLElement[];
  return [selector];
}

function toElementArray(
  selector: string | HTMLElement[] | NodeListOf<Element>
): HTMLElement[] {
  if (typeof selector === "string") {
    return Array.from(document.querySelectorAll<HTMLElement>(selector));
  }
  if (Array.isArray(selector)) return selector as HTMLElement[];
  return Array.from(selector) as HTMLElement[];
}

// ─── Utility: Format number with locale ───

function formatNumber(value: number, decimals: number): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
