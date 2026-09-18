"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface GroundStationStripProps {
  state: DemoState | null;
}

export default function GroundStationStrip({ state }: GroundStationStripProps) {
  const stations = state?.groundStations ?? [];

  return (
    <div className="flex items-stretch gap-1 overflow-x-auto">
      {stations.map((gs) => (
        <div
          key={gs.id}
          className={`flex-1 min-w-[120px] px-2 py-1.5 rounded border transition-colors ${
            gs.isLinked
              ? "bg-mission-success/10 border-mission-success/30"
              : gs.isVisible
              ? "bg-mission-accent/5 border-mission-accent/20"
              : "bg-slate-800/30 border-slate-700/50"
          }`}
        >
          <div className="flex items-center justify-between mb-0.5">
            <span
              className={`text-[9px] font-bold tracking-wider ${
                gs.isLinked
                  ? "text-mission-success"
                  : gs.isVisible
                  ? "text-mission-accent"
                  : "text-slate-500"
              }`}
            >
              {gs.name}
            </span>
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                gs.isLinked
                  ? "bg-mission-success animate-pulse"
                  : gs.isVisible
                  ? "bg-mission-accent"
                  : "bg-slate-600"
              }`}
            />
          </div>
          <span
            className={`text-[8px] font-mono font-bold tracking-wider ${
              gs.isLinked
                ? "text-mission-success"
                : gs.isVisible
                ? "text-mission-accent"
                : "text-slate-600"
            }`}
          >
            {gs.isLinked ? "LINKED" : gs.isVisible ? "VISIBLE" : "STANDBY"}
          </span>
        </div>
      ))}
    </div>
  );
}
