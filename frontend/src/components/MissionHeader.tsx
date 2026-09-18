"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface MissionHeaderProps {
  state: DemoState | null;
}

export default function MissionHeader({ state }: MissionHeaderProps) {
  const sc = state?.spacecraft;
  const health = state?.health;
  const elapsed = state?.missionElapsed ?? 0;

  const h = Math.floor(elapsed / 3600);
  const m = Math.floor((elapsed % 3600) / 60);
  const s = Math.floor(elapsed % 60);
  const elapsedStr = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;

  const overallStatus = !health
    ? "UNKNOWN"
    : Object.values(health).every((v) => v === "NOMINAL" || v === "ACTIVE" || v === "LINKED" || v === "LOCKED" || v === "READY" || v === "ONLINE" || v === "NADIR")
    ? "NOMINAL"
    : Object.values(health).some((v) => v === "OFFLINE" || v === "CRITICAL")
    ? "CRITICAL"
    : "WARNING";

  const commsStatus = health?.comms ?? "UNKNOWN";

  return (
    <header className="h-9 bg-mission-panel/80 backdrop-blur border-b border-mission-border px-3 flex items-center justify-between shrink-0 select-none">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-mission-accent animate-pulse" />
          <span className="text-[11px] font-bold tracking-wider text-slate-100">
            <span className="text-mission-accent">{sc?.id ?? "CUBESAT-2U-001"}</span>
          </span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">{sc?.mission ?? "WILDFIRE DETECTION"}</span>
        <div className="w-px h-4 bg-slate-700" />
        <span className="text-[10px] text-slate-400">
          MET: <span className="font-mono text-slate-100">{elapsedStr}</span>
        </span>
        <div className="w-px h-4 bg-slate-700" />
        <span className="text-[10px] text-slate-400">
          ORBIT: <span className="font-mono text-mission-accent">LEO/SSO</span>
        </span>
        <span className="text-[10px] text-slate-400">
          ALT: <span className="font-mono text-slate-100">{sc?.altitudeKm ?? 501} KM</span>
        </span>
        <span className="text-[10px] text-slate-400">
          MODE: <span className="font-mono text-slate-100">{sc?.mode ?? "CRUISE"}</span>
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${
              overallStatus === "NOMINAL"
                ? "bg-mission-success"
                : overallStatus === "WARNING"
                ? "bg-mission-warning"
                : "bg-mission-danger"
            }`}
          />
          <span
            className={`text-[10px] font-bold tracking-wider ${
              overallStatus === "NOMINAL"
                ? "text-mission-success"
                : overallStatus === "WARNING"
                ? "text-mission-warning"
                : "text-mission-danger"
            }`}
          >
            SYS: {overallStatus}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${
              commsStatus === "LINKED" || commsStatus === "NOMINAL"
                ? "bg-mission-success"
                : commsStatus === "STANDBY"
                ? "bg-slate-500"
                : "bg-mission-danger"
            }`}
          />
          <span
            className={`text-[10px] font-bold tracking-wider ${
              commsStatus === "LINKED" || commsStatus === "NOMINAL"
                ? "text-mission-success"
                : commsStatus === "STANDBY"
                ? "text-slate-400"
                : "text-mission-danger"
            }`}
          >
            COMMS: {commsStatus}
          </span>
        </div>

        <div className="px-2 py-0.5 rounded bg-mission-accent/15 border border-mission-accent/30">
          <span className="text-[9px] font-bold tracking-widest text-mission-accent">DEMO MODE</span>
        </div>
      </div>
    </header>
  );
}
