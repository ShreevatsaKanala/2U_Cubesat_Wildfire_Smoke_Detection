"use client";
import React, { useEffect, useCallback } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchEvents } from "@/lib/api";
import { Activity } from "lucide-react";

const severityColor = (s: string) => {
  if (s === "CRITICAL") return "border-l-mission-danger bg-red-900/20";
  if (s === "ERROR") return "border-l-mission-danger bg-red-900/10";
  if (s === "WARNING") return "border-l-mission-warning bg-yellow-900/10";
  return "border-l-slate-600 bg-slate-800/30";
};

const severityText = (s: string) => {
  if (s === "CRITICAL") return "text-mission-danger";
  if (s === "ERROR") return "text-mission-danger";
  if (s === "WARNING") return "text-mission-warning";
  return "text-slate-400";
};

export default function MissionEventsPanel() {
  const { events, setEvents } = useMissionStore();

  const loadEvents = useCallback(() => {
    fetchEvents(50)
      .then((data) => setEvents(data.map((e) => ({ ...e, data: e.data as Record<string, unknown> | null }))))
      .catch(() => {});
  }, [setEvents]);

  useEffect(() => {
    loadEvents();
    const id = setInterval(loadEvents, 10000);
    return () => clearInterval(id);
  }, [loadEvents]);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Activity size={12} /> Mission Events
      </h3>
      <div className="max-h-48 overflow-y-auto space-y-1">
        {events.length === 0 && <p className="text-slate-500 text-[11px]">No events recorded</p>}
        {events.map((e) => (
          <div key={e.id} className={`border-l-2 ${severityColor(e.severity)} px-2 py-1 rounded-r`}>
            <div className="flex justify-between items-start">
              <span className={`text-[10px] font-mono font-bold ${severityText(e.severity)}`}>{e.severity}</span>
              <span className="text-[9px] text-slate-600 font-mono">{new Date(e.timestamp).toLocaleTimeString()}</span>
            </div>
            <p className="text-[10px] text-slate-300 leading-tight">{e.message}</p>
            <span className="text-[9px] text-slate-500">{e.event_type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
