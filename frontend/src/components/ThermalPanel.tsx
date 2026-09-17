"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { Thermometer } from "lucide-react";

export default function ThermalPanel() {
  const t = useMissionStore((s) => s.telemetry);
  if (!t) return <div className="panel"><p className="text-slate-500 text-xs">Awaiting telemetry...</p></div>;

  const nodes = t.thermal.nodes;
  const allTemps = nodes.map((n) => n.temperature_c);
  const minT = Math.min(...allTemps, -20);
  const maxT = Math.max(...allTemps, 60);
  const range = maxT - minT || 1;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Thermometer size={12} /> Thermal
      </h3>
      {nodes.map((node) => {
        const safeMinPct = ((node.min_safe_c - minT) / range) * 100;
        const safeMaxPct = ((node.max_safe_c - minT) / range) * 100;
        const tempPct = ((node.temperature_c - minT) / range) * 100;
        const inSafe = node.temperature_c >= node.min_safe_c && node.temperature_c <= node.max_safe_c;
        const nearHigh = node.temperature_c > node.max_safe_c - 5;
        const barColor = inSafe ? (nearHigh ? "bg-mission-warning" : "bg-mission-success") : "bg-mission-danger";

        return (
          <div key={node.name} className="space-y-0.5">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400 truncate">{node.name.replace(/_/g, " ")}</span>
              <span className={`font-mono font-bold ${inSafe ? (nearHigh ? "text-mission-warning" : "text-slate-200") : "text-mission-danger"}`}>
                {node.temperature_c.toFixed(1)}°C
              </span>
            </div>
            <div className="relative w-full h-2 bg-slate-700 rounded-full overflow-hidden">
              <div className="absolute h-full bg-slate-600 rounded" style={{ left: `${safeMinPct}%`, width: `${safeMaxPct - safeMinPct}%` }} />
              <div className={`absolute h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${tempPct}%` }} />
            </div>
            <div className="flex justify-between text-[9px] text-slate-600">
              <span>{node.min_safe_c}°C</span>
              <span>{node.max_safe_c}°C</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
