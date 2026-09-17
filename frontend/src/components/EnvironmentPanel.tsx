"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";

export default function EnvironmentPanel() {
  const t = useMissionStore((s) => s.telemetry);
  if (!t) return <div className="panel"><p className="text-slate-500 text-sm">Awaiting position data...</p></div>;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider">Environmental Context</h3>
      <div className="text-xs text-slate-400">
        <p>Position: {t.latitude.toFixed(4)}°, {t.longitude.toFixed(4)}°</p>
        <p className="mt-1 text-slate-500">Weather and air quality data available via API.</p>
        <p className="text-slate-500">FIRMS hotspot data will display on the globe when available.</p>
      </div>
    </div>
  );
}
