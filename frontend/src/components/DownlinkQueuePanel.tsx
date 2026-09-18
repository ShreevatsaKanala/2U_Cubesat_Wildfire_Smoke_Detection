"use client";
import React, { useEffect, useCallback } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchDownlinkStatus } from "@/lib/api";
import { Download } from "lucide-react";

const STATUS_LABELS: Record<string, string> = {
  queued: "QUEUED",
  transferring: "TRANSMITTING",
  paused: "PAUSED",
  transmitted: "COMPLETE",
  failed: "FAILED",
};

const STATUS_COLORS: Record<string, string> = {
  queued: "text-slate-400",
  transferring: "text-mission-warning",
  paused: "text-blue-400",
  transmitted: "text-mission-success",
  failed: "text-mission-danger",
};

function formatBand(band: string): string {
  switch (band) {
    case "s_band":
      return "S-Band";
    case "x_band":
      return "X-Band";
    case "ka_band":
      return "Ka-Band";
    default:
      return band;
  }
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function formatRate(bytesPerSec: number): string {
  if (bytesPerSec >= 1024 * 1024) return `${(bytesPerSec / (1024 * 1024)).toFixed(0)} MB/s`;
  if (bytesPerSec >= 1024) return `${(bytesPerSec / 1024).toFixed(0)} KB/s`;
  return `${bytesPerSec.toFixed(0)} B/s`;
}

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

  if (!downlinkQueue) {
    return (
      <div className="panel space-y-2">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
          <Download size={12} /> Downlink Queue
        </h3>
        <p className="text-slate-500 text-xs">Loading...</p>
      </div>
    );
  }

  const { items, total_transmitted, effective_rate_bytes_s, current_band, progress } = downlinkQueue;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Download size={12} /> Downlink Queue
      </h3>

      <div className="flex flex-wrap gap-3 text-[10px]">
        <span className="text-slate-400">
          TX: <span className="font-mono text-mission-success">{total_transmitted}</span>
        </span>
        <span className="text-slate-400">
          Band: <span className="font-mono text-slate-300">{formatBand(current_band)}</span>
        </span>
        <span className="text-slate-400">
          Rate: <span className="font-mono text-slate-300">{formatRate(effective_rate_bytes_s)}</span>
        </span>
        <span className="text-slate-400">
          Progress: <span className="font-mono text-slate-300">{progress.overall_progress_pct.toFixed(1)}%</span>
        </span>
      </div>

      {progress.total_active_bytes > 0 && (
        <div className="w-full bg-mission-dark rounded-full h-1.5">
          <div
            className="bg-mission-accent h-1.5 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(progress.overall_progress_pct, 100)}%` }}
          />
        </div>
      )}

      <div className="max-h-32 overflow-y-auto space-y-1">
        {items.length === 0 && (
          <p className="text-slate-500 text-[11px]">Queue empty</p>
        )}
        {items.map((item) => (
          <div
            key={item.observation_id}
            className="flex items-center justify-between px-2 py-1 rounded bg-mission-dark border border-mission-border text-[10px]"
          >
            <div className="flex-1 min-w-0">
              <span className="font-mono text-slate-300 truncate block">
                {item.observation_id}
              </span>
              <span className="text-slate-600">
                {formatBytes(item.image_size_bytes)} · {item.priority}
                {item.assigned_station && ` · ${item.assigned_station}`}
              </span>
              {item.status === "transferring" && item.progress_pct > 0 && (
                <div className="flex items-center gap-1 mt-0.5">
                  <div className="w-16 bg-slate-700 rounded-full h-1">
                    <div
                      className="bg-mission-warning h-1 rounded-full"
                      style={{ width: `${item.progress_pct}%` }}
                    />
                  </div>
                  <span className="text-slate-500">{item.progress_pct.toFixed(0)}%</span>
                </div>
              )}
              {item.status === "paused" && item.pause_reason && (
                <span className="text-blue-400 text-[9px]">
                  {item.pause_reason.replace(/_/g, " ")}
                </span>
              )}
            </div>
            <span
              className={`font-mono font-bold ml-2 ${STATUS_COLORS[item.status] || "text-slate-400"}`}
            >
              {STATUS_LABELS[item.status] || item.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
