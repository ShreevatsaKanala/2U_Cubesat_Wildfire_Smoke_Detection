"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchObservations } from "@/lib/api";
import { History, Play, ChevronLeft, ChevronRight } from "lucide-react";

const priorityColors: Record<string, string> = {
  LOW: "text-slate-400",
  MEDIUM: "text-mission-warning",
  HIGH: "text-orange-500",
  CRITICAL: "text-mission-critical",
};

export default function ObservationHistoryPanel() {
  const { replayMode, setReplayMode, replayIndex, setReplayIndex } = useMissionStore();
  const [obs, setObs] = useState<{ observation_id: string; timestamp: string; latitude: number; longitude: number; smoke_probability: number | null; priority: string; processing_status: string }[]>([]);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 10;
  const totalPages = Math.ceil(total / limit);

  const load = useCallback(() => {
    fetchObservations(limit, page * limit)
      .then((r) => { setObs(r.observations); setTotal(r.total); })
      .catch(() => {});
  }, [page]);

  useEffect(() => { load(); }, [load]);

  const handleReplay = (idx: number) => {
    setReplayIndex(idx);
    setReplayMode(true);
  };

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <History size={12} /> Observation History
      </h3>
      <div className="max-h-48 overflow-y-auto space-y-1">
        {obs.length === 0 && <p className="text-slate-500 text-[11px]">No observations</p>}
        {obs.map((o, i) => (
          <div key={o.observation_id} className="flex items-center justify-between px-2 py-1 rounded bg-mission-dark border border-mission-border text-[10px] hover:border-slate-600 transition-colors">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono text-slate-300">{new Date(o.timestamp).toLocaleTimeString()}</span>
                <span className={`font-bold ${priorityColors[o.priority] || "text-slate-400"}`}>{o.priority}</span>
              </div>
              <div className="text-slate-500 font-mono">{o.latitude.toFixed(2)}°, {o.longitude.toFixed(2)}°</div>
            </div>
            <button onClick={() => handleReplay(page * limit + i)}
              className="p-1 rounded hover:bg-mission-accent/20 text-slate-400 hover:text-mission-accent transition-colors">
              <Play size={12} />
            </button>
          </div>
        ))}
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
            className="p-1 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-slate-300">
            <ChevronLeft size={14} />
          </button>
          <span className="text-[10px] text-slate-500">{page + 1}/{totalPages}</span>
          <button onClick={() => setPage(Math.min(totalPages - 1, page + 1))} disabled={page >= totalPages - 1}
            className="p-1 rounded bg-slate-700 hover:bg-slate-600 disabled:opacity-30 text-slate-300">
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
