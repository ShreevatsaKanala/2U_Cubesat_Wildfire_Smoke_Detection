"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface PowerPanelProps {
  state: DemoState | null;
}

export default function PowerPanel({ state }: PowerPanelProps) {
  const power = state?.power;

  if (!power) {
    return (
      <div className="panel">
        <div className="text-[10px] text-slate-500 font-mono">INITIALIZING...</div>
      </div>
    );
  }

  const soc = power.batterySoc;
  const socColor =
    soc > 50 ? "bg-mission-success" : soc > 20 ? "bg-mission-warning" : "bg-mission-danger";
  const socTextColor =
    soc > 50 ? "text-mission-success" : soc > 20 ? "text-mission-warning" : "text-mission-danger";
  const balanceColor = power.powerBalanceW >= 0 ? "text-mission-success" : "text-mission-danger";

  return (
    <div className="panel space-y-2">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest">
        Power
      </h3>

      <div className="space-y-1">
        <div className="flex justify-between items-baseline">
          <span className="text-[10px] text-slate-400">Battery</span>
          <span className={`text-xl font-mono font-bold ${socTextColor}`}>
            {soc.toFixed(0)}
            <span className="text-sm">%</span>
          </span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
          <div
            className={`h-full ${socColor} rounded-full transition-all duration-1000`}
            style={{ width: `${soc}%` }}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between text-[10px]">
          <span className="text-slate-400">Solar</span>
          <span className="font-mono text-slate-100">{power.solarGenerationW.toFixed(1)} W</span>
        </div>
        <div className="flex justify-between text-[10px]">
          <span className="text-slate-400">Load</span>
          <span className="font-mono text-slate-100">{power.powerConsumptionW.toFixed(1)} W</span>
        </div>
        <div className="flex justify-between text-[10px]">
          <span className="text-slate-400">Net</span>
          <span className={`font-mono font-bold ${balanceColor}`}>
            {power.powerBalanceW >= 0 ? "+" : ""}
            {power.powerBalanceW.toFixed(1)} W
          </span>
        </div>
        <div className="flex justify-between text-[10px]">
          <span className="text-slate-400">State</span>
          <span
            className={`font-mono font-bold text-[10px] ${
              power.chargeState === "CHARGING"
                ? "text-mission-success"
                : power.chargeState === "DISCHARGING"
                ? "text-mission-warning"
                : "text-slate-300"
            }`}
          >
            {power.chargeState}
          </span>
        </div>
      </div>
    </div>
  );
}
