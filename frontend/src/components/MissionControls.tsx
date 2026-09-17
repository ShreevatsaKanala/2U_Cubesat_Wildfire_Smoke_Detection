"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { startSimulation, stopSimulation, resetSimulation } from "@/lib/api";

export default function MissionControls() {
  const { simulationRunning, setSimulationRunning, clearHistory } = useMissionStore();

  const handleStart = async () => { await startSimulation(); setSimulationRunning(true); };
  const handleStop = async () => { await stopSimulation(); setSimulationRunning(false); };
  const handleReset = async () => { await resetSimulation(); setSimulationRunning(false); clearHistory(); };

  return (
    <div className="panel space-y-3">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider">Mission Controls</h3>
      <div className="flex gap-2">
        <button onClick={handleStart} disabled={simulationRunning} className="flex-1 px-3 py-2 bg-green-700 hover:bg-green-600 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded transition-colors">
          START
        </button>
        <button onClick={handleStop} disabled={!simulationRunning} className="flex-1 px-3 py-2 bg-red-700 hover:bg-red-600 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded transition-colors">
          STOP
        </button>
        <button onClick={handleReset} className="flex-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium rounded transition-colors">
          RESET
        </button>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Status:</span>
        <span className={`text-xs font-medium ${simulationRunning ? "text-mission-success" : "text-slate-500"}`}>
          {simulationRunning ? "RUNNING" : "STOPPED"}
        </span>
      </div>
    </div>
  );
}
