"use client";
import React, { useEffect, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchObservations } from "@/lib/api";
import { Eye, ChevronLeft, ChevronRight } from "lucide-react";

const priorityColors: Record<string, string> = {
  LOW: "text-slate-400",
  MEDIUM: "text-mission-warning",
  HIGH: "text-orange-500",
  CRITICAL: "text-mission-critical",
};

export default function ObservationCenter() {
  const obs = useMissionStore((s) => s.observations)[0];
  const setObservations = useMissionStore((s) => s.setObservations);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 10;

  useEffect(() => {
    fetchObservations(limit, page * limit)
      .then((r) => {
        setObservations(r.observations);
        setTotal(r.total);
      })
      .catch(() => {});
  }, [page, setObservations]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="panel space-y-3">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Eye size={12} /> Observation Center
      </h3>
      {obs ? (
        <>
          <div className="grid grid-cols-2 gap-1 text-[11px]">
            <div><span className="text-slate-500">ID:</span> <span className="font-mono text-slate-200">{obs.observation_id}</span></div>
            <div><span className="text-slate-500">Time:</span> <span className="font-mono text-slate-200">{new Date(obs.timestamp).toLocaleTimeString()}</span></div>
            <div><span className="text-slate-500">Lat:</span> <span className="font-mono text-slate-200">{obs.latitude.toFixed(4)}°</span></div>
            <div><span className="text-slate-500">Lon:</span> <span className="font-mono text-slate-200">{obs.longitude.toFixed(4)}°</span></div>
          </div>
          {obs.image_path && (
            <div className="bg-mission-dark rounded p-1">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`http://localhost:8000/${obs.image_path}`} alt="Observation" className="w-full h-28 object-cover rounded" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-1 text-[11px]">
            <div><span className="text-slate-500">Smoke:</span> <span className="font-mono text-slate-200">{obs.smoke_probability?.toFixed(3) ?? "—"}</span></div>
            <div><span className="text-slate-500">Confidence:</span> <span className="font-mono text-slate-200">{obs.confidence?.toFixed(3) ?? "—"}</span></div>
            <div><span className="text-slate-500">Priority:</span> <span className={`font-bold ${priorityColors[obs.priority] || "text-slate-200"}`}>{obs.priority}</span></div>
            <div><span className="text-slate-500">Model:</span> <span className="font-mono text-slate-200">{obs.model_name}</span></div>
            <div><span className="text-slate-500">Latency:</span> <span className="font-mono text-slate-200">{obs.inference_latency_ms?.toFixed(0) ?? "—"} ms</span></div>
            <div><span className="text-slate-500">Status:</span> <span className="font-mono text-slate-200">{obs.processing_status}</span></div>
          </div>
          {(obs.priority === "CRITICAL" || obs.priority === "HIGH") && (
            <div className="text-[11px] p-1.5 rounded bg-red-900/30 border border-red-800 text-red-300">
              Probable smoke signature — requires ground verification
            </div>
          )}
        </>
      ) : (
        <p className="text-slate-500 text-xs">No observations yet</p>
      )}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
            className="p-1 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-slate-300">
            <ChevronLeft size={14} />
          </button>
          <span className="text-[10px] text-slate-500">Page {page + 1} of {totalPages} ({total} total)</span>
          <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
            className="p-1 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-slate-300">
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
