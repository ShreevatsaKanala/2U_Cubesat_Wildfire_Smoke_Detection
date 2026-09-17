"use client";
import React, { useEffect, useCallback } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchDownlinkStatus } from "@/lib/api";
import { Download } from "lucide-react";

export default function DownlinkQueuePanel() {
  const { downlinkQueue, setDownlinkQueue } = useMissionStore();

  const load = useCallback(() => {
    fetchDownlinkStatus().then(setDownlinkQueue).catch(() => {});
  }, [setDownlinkQueue]);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  const statusColor = (s: string) => {
    if (s === "completed") return "text-mission-success";
    if (s === "failed") return "text-mission-danger";
    if (s === "transmitting") return "text-mission-warning";
    return "text-slate-400";
  };

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Download size={12} /> Downlink Queue
      </h3>
      {!downlinkQueue ? (
        <p className="text-slate-500 text-xs">Loading...</p>
      ) : (
        <>
          <div className="flex gap-3 text-[10px]">
            <span className="text-slate-400">TX: <span className="font-mono text-mission-success">{downlinkQueue.total_transmitted}</span></span>
            <span className="text-slate-400">Fail: <span className="font-mono text-mission-danger">{downlinkQueue.total_failed}</span></span>
          </div>
          <div className="max-h-32 overflow-y-auto space-y-1">
            {downlinkQueue.queue.length === 0 && <p className="text-slate-500 text-[11px]">Queue empty</p>}
            {downlinkQueue.queue.map((item) => (
              <div key={item.id} className="flex items-center justify-between px-2 py-1 rounded bg-mission-dark border border-mission-border text-[10px]">
                <div className="flex-1 min-w-0">
                  <span className="font-mono text-slate-300 truncate block">{item.observation_id}</span>
                  <span className="text-slate-600">{(item.size_bytes / 1024).toFixed(1)} KB · {item.priority}</span>
                </div>
                <span className={`font-mono font-bold ml-2 ${statusColor(item.status)}`}>{item.status}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
