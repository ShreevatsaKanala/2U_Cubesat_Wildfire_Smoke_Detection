"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface ObservationCenterProps {
  state: DemoState | null;
}

const PRIORITY_COLORS: Record<string, string> = {
  LOW: "text-slate-400",
  MEDIUM: "text-mission-warning",
  HIGH: "text-orange-500",
  CRITICAL: "text-mission-danger",
};

export default function ObservationCenter({ state }: ObservationCenterProps) {
  const observations = state?.observations ?? [];
  const latest = observations[0];

  if (!latest) {
    return (
      <div className="panel space-y-2">
        <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest">
          Latest Observation
        </h3>
        <div className="text-[10px] text-slate-500 font-mono">NO OBSERVATIONS</div>
      </div>
    );
  }

  return (
    <div className="panel space-y-2">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest">
        Latest Observation
      </h3>

      <div className="space-y-1">
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">ID</span>
          <span className="text-[11px] font-mono font-bold text-mission-accent">{latest.id}</span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Time</span>
          <span className="text-[10px] font-mono text-slate-200">{latest.timestamp}</span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Location</span>
          <span className="text-[10px] font-mono text-slate-200">
            {latest.latitude.toFixed(2)}° {latest.latitude >= 0 ? "N" : "S"}{" "}
            {latest.longitude.toFixed(2)}° {latest.longitude >= 0 ? "E" : "W"}
          </span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Altitude</span>
          <span className="text-[10px] font-mono text-slate-200">{latest.altitudeKm} KM</span>
        </div>
      </div>

      <div className="border-t border-mission-border pt-2 space-y-1">
        <div className="flex justify-between items-baseline py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">AI Score</span>
          <span
            className={`text-sm font-mono font-bold ${
              latest.smokeScore > 0.8
                ? "text-mission-danger"
                : latest.smokeScore > 0.6
                ? "text-mission-warning"
                : "text-mission-success"
            }`}
          >
            {latest.smokeScore.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Priority</span>
          <span className={`text-[10px] font-mono font-bold ${PRIORITY_COLORS[latest.priority] ?? "text-slate-200"}`}>
            {latest.priority}
          </span>
        </div>
      </div>
    </div>
  );
}
