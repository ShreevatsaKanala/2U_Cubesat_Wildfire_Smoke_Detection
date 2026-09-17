"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";

export default function ObservationCenter() {
  const obs = useMissionStore((s) => s.observations)[0];
  const t = useMissionStore((s) => s.telemetry);

  const priorityColors: Record<string, string> = {
    LOW: "text-slate-400",
    MEDIUM: "text-mission-warning",
    HIGH: "text-orange-500",
    CRITICAL: "text-mission-critical",
  };

  return (
    <div className="panel space-y-3">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider">Observation Center</h3>
      {obs ? (
        <>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div><span className="text-slate-500">ID:</span> <span className="font-mono text-slate-200">{obs.observation_id}</span></div>
            <div><span className="text-slate-500">Time:</span> <span className="font-mono text-slate-200">{new Date(obs.timestamp).toLocaleTimeString()}</span></div>
            <div><span className="text-slate-500">Lat:</span> <span className="font-mono text-slate-200">{obs.latitude.toFixed(4)}°</span></div>
            <div><span className="text-slate-500">Lon:</span> <span className="font-mono text-slate-200">{obs.longitude.toFixed(4)}°</span></div>
          </div>
          {obs.image_path && (
            <div className="bg-mission-dark rounded p-2">
              <img src={`http://localhost:8000/${obs.image_path}`} alt="Observation" className="w-full h-32 object-cover rounded" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div><span className="text-slate-500">Smoke Prob:</span> <span className="font-mono text-slate-200">{obs.smoke_probability?.toFixed(3) ?? "—"}</span></div>
            <div><span className="text-slate-500">Confidence:</span> <span className="font-mono text-slate-200">{obs.confidence?.toFixed(3) ?? "—"}</span></div>
            <div><span className="text-slate-500">Priority:</span> <span className={`font-bold ${priorityColors[obs.priority] || "text-slate-200"}`}>{obs.priority}</span></div>
            <div><span className="text-slate-500">Model:</span> <span className="font-mono text-slate-200">{obs.model_name}</span></div>
            <div><span className="text-slate-500">Latency:</span> <span className="font-mono text-slate-200">{obs.inference_latency_ms?.toFixed(0)} ms</span></div>
            <div><span className="text-slate-500">Status:</span> <span className="font-mono text-slate-200">{obs.processing_status}</span></div>
          </div>
          {obs.priority === "CRITICAL" || obs.priority === "HIGH" ? (
            <div className="text-xs p-2 rounded bg-red-900/30 border border-red-800 text-red-300">
              Probable smoke signature — requires ground verification
            </div>
          ) : null}
        </>
      ) : (
        <p className="text-slate-500 text-sm">No observations yet</p>
      )}
    </div>
  );
}
