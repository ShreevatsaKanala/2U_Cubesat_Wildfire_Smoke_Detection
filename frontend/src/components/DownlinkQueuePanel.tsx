"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface DownlinkQueuePanelProps {
  state: DemoState | null;
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

export default function DownlinkQueuePanel({ state }: DownlinkQueuePanelProps) {
  const downlink = state?.downlink;

  if (!downlink) {
    return (
      <div className="panel">
        <div className="text-[10px] text-slate-500 font-mono">INITIALIZING...</div>
      </div>
    );
  }

  const { items, totalTransmitted, effectiveRateBytesS, currentBand, progress } = downlink;
  const linkedStation = state?.groundStations?.find((gs) => gs.isLinked);

  return (
    <div className="panel space-y-2">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest">
        Downlink
      </h3>

      <div className="space-y-1">
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Station</span>
          <span className={`text-[10px] font-mono font-bold ${linkedStation ? "text-mission-success" : "text-slate-500"}`}>
            {linkedStation?.name ?? "NONE"}
          </span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Band</span>
          <span className="text-[10px] font-mono text-slate-200">{currentBand}</span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">Rate</span>
          <span className="text-[10px] font-mono text-slate-200">
            {effectiveRateBytesS > 0 ? formatRate(effectiveRateBytesS) : "---"}
          </span>
        </div>
        <div className="flex justify-between py-0.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">TX</span>
          <span className="text-[10px] font-mono text-mission-success">{totalTransmitted}</span>
        </div>
      </div>

      {progress.activeCount > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between text-[10px]">
            <span className="text-slate-400">Progress</span>
            <span className="font-mono text-slate-200">{progress.overallProgressPct.toFixed(1)}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
            <div
              className="h-full bg-mission-accent rounded-full transition-all duration-500"
              style={{ width: `${Math.min(progress.overallProgressPct, 100)}%` }}
            />
          </div>
        </div>
      )}

      <div className="space-y-1 max-h-28 overflow-y-auto">
        {items.length === 0 ? (
          <div className="text-[9px] text-slate-600 font-mono text-center py-1">QUEUE EMPTY</div>
        ) : (
          items.slice(0, 5).map((item) => (
            <div
              key={item.observationId}
              className="flex items-center justify-between px-1.5 py-1 rounded bg-slate-800/50 border border-slate-700/50"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[9px] font-mono text-slate-300">{item.observationId}</span>
                  <span className="text-[8px] text-slate-600">{formatBytes(item.sizeBytes)}</span>
                </div>
                {item.status === "transmitting" && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <div className="w-16 h-1 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-mission-accent rounded-full"
                        style={{ width: `${item.progressPct}%` }}
                      />
                    </div>
                    <span className="text-[8px] text-slate-500 font-mono">{item.progressPct.toFixed(0)}%</span>
                  </div>
                )}
                {item.status === "paused" && (
                  <span className="text-[8px] text-mission-warning font-mono">PAUSED</span>
                )}
              </div>
              <span
                className={`text-[8px] font-mono font-bold ml-1.5 ${
                  item.status === "transmitting"
                    ? "text-mission-warning"
                    : item.status === "paused"
                    ? "text-slate-500"
                    : "text-slate-400"
                }`}
              >
                {item.status === "transmitting" ? "TX" : item.status === "paused" ? "PAUSED" : "QUEUED"}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
