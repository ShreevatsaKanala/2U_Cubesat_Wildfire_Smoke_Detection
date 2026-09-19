"use client";
import { useEffect, useRef, useCallback, useState } from "react";
import { DemoEngine, type DemoState } from "@/lib/demoEngine";

const initialEngine = new DemoEngine();
const initialState: DemoState = initialEngine.getState();

export function useDemoEngine() {
  const engineRef = useRef<DemoEngine>(initialEngine);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [state, setState] = useState<DemoState>(initialState);

  const tick = useCallback(() => {
    const engine = engineRef.current;
    engine.tick();
    setState({ ...engine.getState() });
  }, []);

  const start = useCallback(() => {
    const engine = engineRef.current;
    engine.start();
    setState({ ...engine.getState() });
    if (!intervalRef.current) {
      intervalRef.current = setInterval(tick, 1000);
    }
  }, [tick]);

  const pause = useCallback(() => {
    const engine = engineRef.current;
    engine.pause();
    setState({ ...engine.getState() });
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    const engine = engineRef.current;
    engine.reset();
    setState({ ...engine.getState() });
  }, []);

  const setSpeed = useCallback((speed: number) => {
    engineRef.current.setSpeed(speed);
    setState({ ...engineRef.current.getState() });
  }, []);

  const setScenario = useCallback((scenario: string) => {
    engineRef.current.setScenario(scenario);
    setState({ ...engineRef.current.getState() });
  }, []);

  const injectFault = useCallback((type: "commLoss" | "lowBattery" | "thermalWarning") => {
    engineRef.current.injectFault(type);
    setState({ ...engineRef.current.getState() });
  }, []);

  const clearFaults = useCallback(() => {
    engineRef.current.clearFaults();
    setState({ ...engineRef.current.getState() });
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
