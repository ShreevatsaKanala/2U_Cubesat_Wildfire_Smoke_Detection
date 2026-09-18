"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface AIVisionPanelProps {
  state: DemoState | null;
}

export default function AIVisionPanel({ state }: AIVisionPanelProps) {
  const ai = state?.ai;

  if (!ai) {
    return (
      <div className="panel">
        <div className="text-[10px] text-slate-500 font-mono">INITIALIZING...</div>
      </div>
    );
  }

  const smokeColor =
    ai.smokeScore > 0.8
      ? "text-mission-danger"
      : ai.smokeScore > 0.6
      ? "text-mission-warning"
      : "text-mission-success";

  const smokeDot =
    ai.smokeScore > 0.8
      ? "bg-mission-danger"
      : ai.smokeScore > 0.6
      ? "bg-mission-warning"
      : "bg-mission-success";

  return (
    <div className="panel space-y-2">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest flex items-center gap-1.5">
        Vision AI
      </h3>

      <div className="space-y-1">
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Status</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-mission-success animate-pulse" />
            <span className="text-[10px] font-mono font-bold text-mission-success">{ai.status}</span>
          </div>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Model</span>
          <span className="text-[10px] font-mono text-slate-200">{ai.model}</span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Latest</span>
          <span className="text-[10px] font-mono text-mission-accent">{ai.latestObservationId ?? "NONE"}</span>
        </div>
      </div>

      <div className="border-t border-mission-border pt-2 space-y-1">
        <div className="flex justify-between items-baseline">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Smoke Score</span>
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full ${smokeDot}`} />
            <span className={`text-base font-mono font-bold ${smokeColor}`}>
              {(ai.smokeScore * 100).toFixed(0)}
              <span className="text-xs">%</span>
            </span>
          </div>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Confidence</span>
          <span className="text-[10px] font-mono font-bold text-slate-100">{ai.confidence}</span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Latency</span>
          <span className="text-[10px] font-mono text-slate-200">{ai.latencyMs.toFixed(2)}s</span>
        </div>
      </div>

      {ai.visualEvidence.length > 0 && (
        <div className="border-t border-mission-border pt-2 space-y-1">
          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-semibold">
            Visual Evidence
          </span>
          <ul className="space-y-0.5">
            {ai.visualEvidence.map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[9px] text-slate-300 leading-tight">
                <span className="text-mission-accent shrink-0 mt-0.5">▸</span>
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}

      {ai.alternativeExplanations.length > 0 && (
        <div className="border-t border-mission-border pt-2 space-y-1">
          <span className="text-[9px] text-slate-500 uppercase tracking-widest font-semibold">
            Alternatives
          </span>
          <ul className="space-y-0.5">
            {ai.alternativeExplanations.map((e, i) => (
              <li key={i} className="flex items-start gap-1.5 text-[9px] text-slate-400 leading-tight">
                <span className="text-slate-600 shrink-0 mt-0.5">◇</span>
                {e}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
