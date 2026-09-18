"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface DemoControlsProps {
  state: DemoState | null;
  onStart: () => void;
  onPause: () => void;
  onReset: () => void;
  onSetSpeed: (s: number) => void;
  onSetScenario: (s: string) => void;
  onInjectFault: (type: "commLoss" | "lowBattery" | "thermalWarning") => void;
  onClearFaults: () => void;
}

const SCENARIOS = ["NORMAL", "WILDFIRE", "HIGH PRIORITY", "LOW BATTERY", "THERMAL", "COMM LOSS", "RECOVERY"];
const SPEEDS = [1, 5, 10, 50];

export default function DemoControls({
  state,
  onStart,
  onPause,
  onReset,
  onSetSpeed,
  onSetScenario,
  onInjectFault,
  onClearFaults,
}: DemoControlsProps) {
  const isRunning = state?.running ?? false;
  const currentSpeed = state?.simSpeed ?? 1;
  const currentScenario = state?.scenario ?? "NORMAL";
  const anyFault = state?.faults ? Object.values(state.faults).some(Boolean) : false;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <div className="flex items-center gap-1">
        {!isRunning ? (
          <button
            onClick={onStart}
            className="px-2 py-1 text-[10px] font-bold tracking-wider uppercase rounded bg-mission-success/20 border border-mission-success/40 text-mission-success hover:bg-mission-success/30 transition-colors"
          >
            START
          </button>
        ) : (
          <button
            onClick={onPause}
            className="px-2 py-1 text-[10px] font-bold tracking-wider uppercase rounded bg-mission-warning/20 border border-mission-warning/40 text-mission-warning hover:bg-mission-warning/30 transition-colors"
          >
            PAUSE
          </button>
        )}
        <button
          onClick={onReset}
          className="px-2 py-1 text-[10px] font-bold tracking-wider uppercase rounded bg-slate-700/50 border border-slate-600 text-slate-300 hover:bg-slate-600/50 transition-colors"
        >
          RESET
        </button>
      </div>

      <div className="w-px h-5 bg-slate-700" />

      <div className="flex items-center gap-1">
        <span className="text-[9px] text-slate-500 uppercase mr-1">Speed</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSetSpeed(s)}
            className={`px-1.5 py-0.5 text-[10px] font-mono rounded transition-colors ${
              currentSpeed === s
                ? "bg-mission-accent text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
            }`}
          >
            {s}X
          </button>
        ))}
      </div>

      <div className="w-px h-5 bg-slate-700" />

      <div className="flex items-center gap-1">
        <span className="text-[9px] text-slate-500 uppercase mr-1">Scenario</span>
        <select
          value={currentScenario}
          onChange={(e) => onSetScenario(e.target.value)}
          className="px-1.5 py-0.5 text-[10px] font-mono bg-slate-800 border border-slate-600 rounded text-slate-200 focus:outline-none focus:border-mission-accent"
        >
          {SCENARIOS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="w-px h-5 bg-slate-700" />

      <div className="flex items-center gap-1">
        <span className="text-[9px] text-slate-500 uppercase mr-1">Fault</span>
        <button
          onClick={() => onInjectFault("commLoss")}
          className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
            state?.faults?.commLoss
              ? "bg-mission-danger text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700"
          }`}
        >
          COMMS
        </button>
        <button
          onClick={() => onInjectFault("lowBattery")}
          className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
            state?.faults?.lowBattery
              ? "bg-mission-danger text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700"
          }`}
        >
          BATT
        </button>
        <button
          onClick={() => onInjectFault("thermalWarning")}
          className={`px-1.5 py-0.5 text-[10px] rounded transition-colors ${
            state?.faults?.thermalWarning
              ? "bg-mission-danger text-white"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700"
          }`}
        >
          THERM
        </button>
      </div>

      {anyFault && (
        <>
          <div className="w-px h-5 bg-slate-700" />
          <button
            onClick={onClearFaults}
            className="px-2 py-1 text-[10px] font-bold tracking-wider uppercase rounded bg-mission-danger/20 border border-mission-danger/40 text-mission-danger hover:bg-mission-danger/30 transition-colors"
          >
            CLEAR
          </button>
        </>
      )}
    </div>
  );
}
