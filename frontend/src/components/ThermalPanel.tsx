"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface ThermalPanelProps {
  state: DemoState | null;
}

interface ThermalNode {
  label: string;
  temp: number;
}

function getTrend(temp: number, base: number): string {
  const diff = temp - base;
  if (diff > 1) return "↑";
  if (diff < -1) return "↓";
  return "→";
}

function getTempColor(temp: number): string {
  if (temp > 55) return "text-mission-danger";
  if (temp > 45) return "text-mission-warning";
  return "text-slate-100";
}

function getTempDotColor(temp: number): string {
  if (temp > 55) return "bg-mission-danger";
  if (temp > 45) return "bg-mission-warning";
  return "bg-mission-success";
}

export default function ThermalPanel({ state }: ThermalPanelProps) {
  const thermal = state?.thermal;

  if (!thermal) {
    return (
      <div className="panel">
        <div className="text-[10px] text-slate-500 font-mono">INITIALIZING...</div>
      </div>
    );
  }

  const nodes: ThermalNode[] = [
    { label: "OBC", temp: thermal.obc },
    { label: "CAMERA", temp: thermal.camera },
    { label: "BATTERY", temp: thermal.battery },
    { label: "COMMS", temp: thermal.comms },
    { label: "STRUCTURE", temp: thermal.structure },
  ];

  const baseTemps: Record<string, number> = {
    OBC: 34.2,
    CAMERA: 30.8,
    BATTERY: 28.1,
    COMMS: 32.4,
    STRUCTURE: 24.7,
  };

  return (
    <div className="panel space-y-1.5">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest">
        Thermal
      </h3>
      {nodes.map((node) => (
        <div key={node.label} className="flex items-center justify-between py-0.5">
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${getTempDotColor(node.temp)}`} />
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">{node.label}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`text-[11px] font-mono font-bold ${getTempColor(node.temp)}`}>
              {node.temp.toFixed(1)}°C
            </span>
            <span className="text-[10px] text-slate-500 w-3 text-center">
              {getTrend(node.temp, baseTemps[node.label])}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
