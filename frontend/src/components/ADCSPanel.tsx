"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface ADCSPanelProps {
  state: DemoState | null;
}

export default function ADCSPanel({ state }: ADCSPanelProps) {
  const attitude = state?.attitude;

  if (!attitude) {
    return (
      <div className="panel">
        <div className="text-[10px] text-slate-500 font-mono">INITIALIZING...</div>
      </div>
    );
  }

  const pe = attitude.pointingErrorDeg;
  const peColor = pe < 0.5 ? "text-mission-success" : pe < 1.0 ? "text-mission-warning" : "text-mission-danger";
  const peDot = pe < 0.5 ? "bg-mission-success" : pe < 1.0 ? "bg-mission-warning" : "bg-mission-danger";

  return (
    <div className="panel space-y-1.5">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest">
        ADCS
      </h3>
      <div className="flex items-center gap-1.5 mb-1">
        <div className={`w-1.5 h-1.5 rounded-full ${peDot} animate-pulse`} />
        <span className="text-[10px] font-bold text-mission-success tracking-wider">
          {attitude.mode} LOCK
        </span>
      </div>
      <div className="space-y-0.5">
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Roll</span>
          <span className="text-[11px] font-mono font-bold text-slate-100">
            {attitude.rollDeg >= 0 ? "+" : ""}
            {attitude.rollDeg.toFixed(2)}°
          </span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Pitch</span>
          <span className="text-[11px] font-mono font-bold text-slate-100">
            {attitude.pitchDeg >= 0 ? "+" : ""}
            {attitude.pitchDeg.toFixed(2)}°
          </span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Yaw</span>
          <span className="text-[11px] font-mono font-bold text-slate-100">
            {attitude.yawDeg.toFixed(2)}°
          </span>
        </div>
        <div className="flex justify-between py-0.5 border-t border-mission-border pt-1 mt-1">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Pointing Err</span>
          <span className={`text-[11px] font-mono font-bold ${peColor}`}>
            {attitude.pointingErrorDeg.toFixed(2)}°
          </span>
        </div>
      </div>
    </div>
  );
}
