"use client";
import React, { useEffect, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchObservations } from "@/lib/api";
import { Eye, ChevronLeft, ChevronRight, ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";

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
  const [showEvidence, setShowEvidence] = useState(false);
  const [showAlternatives, setShowAlternatives] = useState(false);
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
  const hasAIFields = obs && obs.ai_provider;

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
          {hasAIFields && (
            <div className="flex gap-1.5">
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-900/40 border border-blue-700 text-blue-400">
                AI VISION
              </span>
              {obs.ai_provider && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                  {obs.ai_provider}
                </span>
              )}
              {obs.ai_model && (
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
                  {obs.ai_model}
                </span>
              )}
            </div>
          )}
          <div className="grid grid-cols-2 gap-1 text-[11px]">
            {hasAIFields && obs.ai_smoke_score !== null && obs.ai_smoke_score !== undefined ? (
              <>
                <div><span className="text-slate-500">AI Smoke:</span> <span className={`font-mono font-bold ${obs.ai_smoke_score > 0.6 ? "text-mission-danger" : "text-slate-200"}`}>{obs.ai_smoke_score?.toFixed(3) ?? "—"}</span></div>
                <div><span className="text-slate-500">Confidence:</span> <span className="font-mono text-slate-200">{obs.ai_confidence ?? "—"}</span></div>
              </>
            ) : (
              <>
                <div><span className="text-slate-500">Smoke:</span> <span className="font-mono text-slate-200">{obs.smoke_probability?.toFixed(3) ?? "—"}</span></div>
                <div><span className="text-slate-500">Confidence:</span> <span className="font-mono text-slate-200">{obs.confidence?.toFixed(3) ?? "—"}</span></div>
              </>
            )}
            <div><span className="text-slate-500">Priority:</span> <span className={`font-bold ${priorityColors[obs.priority] || "text-slate-200"}`}>{obs.priority}</span></div>
            <div>
              <span className="text-slate-500">Model:</span>{" "}
              <span className="font-mono text-slate-200">{obs.model_name}</span>
              {obs.model_version && <span className="font-mono text-slate-400 ml-1">v{obs.model_version}</span>}
            </div>
            {hasAIFields && obs.inference_latency_ms !== null && obs.inference_latency_ms !== undefined ? (
              <div><span className="text-slate-500">AI Latency:</span> <span className="font-mono text-slate-200">{obs.inference_latency_ms?.toFixed(0) ?? "—"} ms</span></div>
            ) : (
              <div><span className="text-slate-500">Latency:</span> <span className="font-mono text-slate-200">{obs.inference_latency_ms?.toFixed(0) ?? "—"} ms</span></div>
            )}
            <div><span className="text-slate-500">Status:</span> <span className="font-mono text-slate-200">{obs.processing_status}</span></div>
          </div>
          {hasAIFields && obs.ai_scene_description && (
            <div className="text-[10px] text-slate-400 italic bg-mission-dark rounded p-1.5">
              {obs.ai_scene_description}
            </div>
          )}
          {hasAIFields && obs.ai_visual_evidence && obs.ai_visual_evidence.length > 0 && (
            <div className="text-[11px]">
              <button
                onClick={() => setShowEvidence(!showEvidence)}
                className="flex items-center gap-1 text-slate-400 hover:text-slate-200"
              >
                {showEvidence ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                Visual Evidence ({obs.ai_visual_evidence.length})
              </button>
              {showEvidence && (
                <ul className="mt-1 ml-3 space-y-0.5 text-[10px] text-slate-300">
                  {obs.ai_visual_evidence.map((e: string, i: number) => (
                    <li key={i} className="list-disc">{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {hasAIFields && obs.ai_alternative_explanations && obs.ai_alternative_explanations.length > 0 && (
            <div className="text-[11px]">
              <button
                onClick={() => setShowAlternatives(!showAlternatives)}
                className="flex items-center gap-1 text-slate-400 hover:text-slate-200"
              >
                {showAlternatives ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                Alternatives ({obs.ai_alternative_explanations.length})
              </button>
              {showAlternatives && (
                <ul className="mt-1 ml-3 space-y-0.5 text-[10px] text-slate-300">
                  {obs.ai_alternative_explanations.map((e: string, i: number) => (
                    <li key={i} className="list-disc">{e}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {hasAIFields && (obs.ai_status === "error" || obs.ai_status === "unavailable") && (
            <div className="flex items-center gap-1.5 text-[11px] p-1.5 rounded bg-yellow-900/30 border border-yellow-800 text-yellow-300">
              <AlertTriangle size={12} />
              AI inference {obs.ai_status}
            </div>
          )}
          {!hasAIFields && obs.model_name && (
            <div className="flex gap-1.5">
              {obs.model_name.toLowerCase().includes("mock") ? (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-yellow-900/40 border border-yellow-700 text-yellow-400">
                  MOCK MODEL
                </span>
              ) : (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-green-900/40 border border-green-700 text-green-400">
                  REAL MODEL
                </span>
              )}
            </div>
          )}
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
