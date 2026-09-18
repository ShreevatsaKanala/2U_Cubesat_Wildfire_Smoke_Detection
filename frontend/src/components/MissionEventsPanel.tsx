"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface MissionEventsPanelProps {
  state: DemoState | null;
}

function severityColor(severity: string): string {
  switch (severity) {
    case "CRITICAL":
      return "border-l-mission-danger bg-red-900/20";
    case "ERROR":
      return "border-l-mission-danger bg-red-900/10";
    case "WARNING":
      return "border-l-mission-warning bg-yellow-900/10";
    default:
      return "border-l-slate-700 bg-slate-800/20";
  }
}

function severityTextColor(severity: string): string {
  switch (severity) {
    case "CRITICAL":
    case "ERROR":
      return "text-mission-danger";
    case "WARNING":
      return "text-mission-warning";
    default:
      return "text-slate-400";
  }
}

function eventTypeColor(type: string): string {
  switch (type) {
    case "OBSERVATION":
      return "text-mission-accent";
    case "AI ANALYSIS":
      return "text-purple-400";
    case "PRIORITY":
      return "text-orange-400";
    case "DOWNLINK":
      return "text-cyan-400";
    case "FAULT":
      return "text-mission-danger";
    case "ORBIT":
      return "text-slate-500";
    default:
      return "text-slate-500";
  }
}

export default function MissionEventsPanel({ state }: MissionEventsPanelProps) {
  const events = state?.events ?? [];

  return (
    <div className="space-y-1">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest mb-1">
        Mission Events
      </h3>
      <div className="overflow-y-auto space-y-0.5 max-h-[140px]">
        {events.length === 0 ? (
          <div className="text-[9px] text-slate-600 font-mono text-center py-2">NO EVENTS</div>
        ) : (
          events.slice(0, 30).map((evt) => (
            <div key={evt.id} className={`border-l-2 ${severityColor(evt.severity)} px-2 py-0.5 rounded-r`}>
              <div className="flex justify-between items-start">
                <span className="text-[8px] font-mono text-slate-600">{evt.timestamp}</span>
                <span className={`text-[8px] font-mono font-bold ${severityTextColor(evt.severity)}`}>
                  {evt.severity}
                </span>
              </div>
              <p className="text-[9px] text-slate-300 leading-tight">{evt.message}</p>
              <span className={`text-[8px] font-mono ${eventTypeColor(evt.type)}`}>{evt.type}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
