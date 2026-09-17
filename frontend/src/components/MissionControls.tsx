"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { startSimulation, stopSimulation, resetSimulation } from "@/lib/api";
import { Play, Square, RotateCcw, Globe, Camera, Zap } from "lucide-react";

export default function MissionControls() {
  const {
    simulationRunning, setSimulationRunning, clearHistory,
    orbitMode, setOrbitMode,
    cameraMode, setCameraMode,
    globeView, setGlobeView,
    simSpeed, setSimSpeed,
  } = useMissionStore();

  const handleStart = async () => { await startSimulation(); setSimulationRunning(true); };
  const handleStop = async () => { await stopSimulation(); setSimulationRunning(false); };
  const handleReset = async () => { await resetSimulation(); setSimulationRunning(false); clearHistory(); };

  const speeds = [1, 2, 5, 10, 20];

  return (
    <div className="panel space-y-3">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider">Mission Controls</h3>
      <div className="flex gap-2">
        <button onClick={handleStart} disabled={simulationRunning} className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-slate-700 disabled:text-slate-500 text-white text-xs font-medium rounded transition-colors">
          <Play size={10} /> START
        </button>
        <button onClick={handleStop} disabled={!simulationRunning} className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-red-700 hover:bg-red-600 disabled:bg-slate-700 disabled:text-slate-500 text-white text-xs font-medium rounded transition-colors">
          <Square size={10} /> STOP
        </button>
        <button onClick={handleReset} className="flex-1 flex items-center justify-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-medium rounded transition-colors">
          <RotateCcw size={10} /> RESET
        </button>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Status:</span>
        <span className={`text-xs font-medium ${simulationRunning ? "text-mission-success" : "text-slate-500"}`}>
          {simulationRunning ? "RUNNING" : "STOPPED"}
        </span>
      </div>

      <div className="space-y-2">
        <h4 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1"><Globe size={10} /> Globe View</h4>
        <div className="flex gap-1">
          {(["follow", "top-down", "free"] as const).map((v) => (
            <button key={v} onClick={() => setGlobeView(v)}
              className={`flex-1 text-[10px] py-1 rounded transition-colors ${globeView === v ? "bg-mission-accent text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
              {v.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1"><Camera size={10} /> Camera Mode</h4>
        <div className="flex gap-1">
          {(["AUTO", "MANUAL", "TRACKING"] as const).map((m) => (
            <button key={m} onClick={() => setCameraMode(m)}
              className={`flex-1 text-[10px] py-1 rounded transition-colors ${cameraMode === m ? "bg-mission-accent text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1"><Zap size={10} /> Orbit Mode</h4>
        <div className="flex gap-1">
          {(["LEO", "SSO", "GEO"] as const).map((m) => (
            <button key={m} onClick={() => setOrbitMode(m)}
              className={`flex-1 text-[10px] py-1 rounded transition-colors ${orbitMode === m ? "bg-mission-accent text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <h4 className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Speed: {simSpeed}x</h4>
        <div className="flex gap-1">
          {speeds.map((s) => (
            <button key={s} onClick={() => setSimSpeed(s)}
              className={`flex-1 text-[10px] py-1 rounded transition-colors ${simSpeed === s ? "bg-mission-accent text-white" : "bg-slate-700 text-slate-400 hover:bg-slate-600"}`}>
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
