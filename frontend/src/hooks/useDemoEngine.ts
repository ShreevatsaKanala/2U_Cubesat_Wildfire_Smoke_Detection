"use client";
import { useEffect, useRef, useCallback, useState } from "react";
import { DemoEngine, type DemoState } from "@/lib/demoEngine";

export function useDemoEngine() {
  const engineRef = useRef<DemoEngine | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [state, setState] = useState<DemoState | null>(null);

  if (!engineRef.current) {
    engineRef.current = new DemoEngine();
  }

  const tick = useCallback(() => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.tick();
    setState({ ...engine.getState() });
  }, []);

  const start = useCallback(() => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.start();
    setState({ ...engine.getState() });
    if (!intervalRef.current) {
      intervalRef.current = setInterval(tick, 1000);
    }
  }, [tick]);

  const pause = useCallback(() => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.pause();
    setState({ ...engine.getState() });
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    const engine = engineRef.current;
    if (!engine) return;
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    engine.reset();
    setState({ ...engine.getState() });
  }, []);

  const setSpeed = useCallback((speed: number) => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.setSpeed(speed);
    setState({ ...engine.getState() });
  }, []);

  const setScenario = useCallback((scenario: string) => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.setScenario(scenario);
    setState({ ...engine.getState() });
  }, []);

  const injectFault = useCallback((type: "commLoss" | "lowBattery" | "thermalWarning") => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.injectFault(type);
    setState({ ...engine.getState() });
  }, []);

  const clearFaults = useCallback(() => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.clearFaults();
    setState({ ...engine.getState() });
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    state,
    start,
    pause,
    reset,
    setSpeed,
    setScenario,
    injectFault,
    clearFaults,
  };
}
