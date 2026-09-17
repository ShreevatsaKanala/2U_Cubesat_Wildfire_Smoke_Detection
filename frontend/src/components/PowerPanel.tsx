"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { Battery, Sun, Zap, Moon } from "lucide-react";

export default function PowerPanel() {
  const t = useMissionStore((s) => s.telemetry);
  if (!t) return <div className="panel"><p className="text-slate-500 text-xs">Awaiting telemetry...</p></div>;

  const p = t.power;
  const socColor = p.battery_soc > 50 ? "bg-mission-success" : p.battery_soc > 20 ? "bg-mission-warning" : "bg-mission-danger";
  const balanceColor = p.power_balance_w >= 0 ? "text-mission-success" : "text-mission-danger";
  const maxPower = Math.max(p.solar_generation_w, p.power_consumption_w, 1);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Battery size={12} /> Power
      </h3>

      <div className="space-y-1">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">Battery</span>
          <span className="font-mono text-slate-200">{p.battery_soc.toFixed(1)}%</span>
        </div>
        <div className="w-full h-2 bg-slate-700 rounded-full overflow-hidden">
          <div className={`h-full ${socColor} rounded-full transition-all duration-500`} style={{ width: `${p.battery_soc}%` }} />
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between items-center text-[11px]">
          <span className="text-slate-400 flex items-center gap-1"><Sun size={10} className="text-yellow-400" /> Solar</span>
          <span className="font-mono text-slate-200">{p.solar_generation_w.toFixed(2)} W</span>
        </div>
        <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div className="h-full bg-yellow-400 rounded-full" style={{ width: `${(p.solar_generation_w / maxPower) * 100}%` }} />
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between items-center text-[11px]">
          <span className="text-slate-400 flex items-center gap-1"><Zap size={10} className="text-blue-400" /> Consumption</span>
          <span className="font-mono text-slate-200">{p.power_consumption_w.toFixed(2)} W</span>
        </div>
        <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
          <div className="h-full bg-blue-400 rounded-full" style={{ width: `${(p.power_consumption_w / maxPower) * 100}%` }} />
        </div>
      </div>

      <div className="flex justify-between items-center text-[11px]">
        <span className="text-slate-400">Balance</span>
        <span className={`font-mono font-bold ${balanceColor}`}>{p.power_balance_w >= 0 ? "+" : ""}{p.power_balance_w.toFixed(2)} W</span>
      </div>

      <div className="flex justify-between items-center text-[11px]">
        <span className="text-slate-400">Voltage</span>
        <span className="font-mono text-slate-200">{p.battery_voltage.toFixed(2)} V</span>
      </div>

      <div className="flex justify-between items-center text-[11px]">
        <span className="text-slate-400 flex items-center gap-1"><Moon size={10} /> Eclipse</span>
        <span className={`font-mono font-bold ${p.eclipse ? "text-mission-warning" : "text-slate-200"}`}>
          {p.eclipse ? "SHADOW" : "SUNLIT"}
        </span>
      </div>

      <div className="flex justify-between items-center text-[11px]">
        <span className="text-slate-400">Batt Temp</span>
        <span className="font-mono text-slate-200">{p.battery_temperature_c.toFixed(1)}°C</span>
      </div>
    </div>
  );
}
