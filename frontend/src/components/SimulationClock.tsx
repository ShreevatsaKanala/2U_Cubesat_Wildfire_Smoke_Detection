"use client";
import React, { useEffect, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { Clock, FastForward } from "lucide-react";

export default function SimulationClock() {
  const { missionStartTime, simSpeed, stepsPerSec, simulationRunning, telemetry } = useMissionStore();
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - missionStartTime) / 1000));
    }, 1000);
    return () => clearInterval(id);
  }, [missionStartTime]);

  const h = Math.floor(elapsed / 3600);
  const m = Math.floor((elapsed % 3600) / 60);
  const s = elapsed % 60;
  const timeStr = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-mission-panel border-t border-mission-border">
      <div className="flex items-center gap-1.5">
        <Clock size={12} className="text-mission-accent" />
        <span className="text-[10px] text-slate-400 uppercase">Mission Time</span>
        <span className="text-xs font-mono text-slate-100">{timeStr}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <FastForward size={12} className="text-mission-accent" />
        <span className="text-[10px] text-slate-400 uppercase">Speed</span>
        <span className="text-xs font-mono text-slate-100">{simSpeed}x</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-slate-400 uppercase">Steps/s</span>
        <span className="text-xs font-mono text-slate-100">{stepsPerSec}</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${simulationRunning ? "bg-mission-success animate-pulse" : "bg-slate-600"}`} />
        <span className={`text-[10px] font-medium uppercase ${simulationRunning ? "text-mission-success" : "text-slate-500"}`}>
          {simulationRunning ? "LIVE" : "IDLE"}
        </span>
      </div>
      {telemetry && (
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="text-[10px] text-slate-400 uppercase">Seq</span>
          <span className="text-xs font-mono text-slate-100">#{telemetry.packet_sequence}</span>
          <span className="text-[10px] text-slate-500">|</span>
          <span className="text-[10px] text-slate-400 uppercase">SC</span>
          <span className="text-xs font-mono text-slate-100">{telemetry.spacecraft_id}</span>
        </div>
      )}
    </div>
  );
}
