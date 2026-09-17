"use client";
import React, { useEffect } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchMLStatus } from "@/lib/api";
import { Brain, Cpu, Activity, AlertTriangle } from "lucide-react";

export default function MLStatusPanel() {
  const mlStatus = useMissionStore((s) => s.mlStatus);
  const setMLStatus = useMissionStore((s) => s.setMLStatus);

  useEffect(() => {
    fetchMLStatus().then((r) => setMLStatus({ mode: r.mode, modelName: r.model_name, modelVersion: r.model_version, modelLoaded: r.model_loaded, threshold: r.threshold })).catch(() => {});
    const id = setInterval(() => {
      fetchMLStatus().then((r) => setMLStatus({ mode: r.mode, modelName: r.model_name, modelVersion: r.model_version, modelLoaded: r.model_loaded, threshold: r.threshold })).catch(() => {});
    }, 10000);
    return () => clearInterval(id);
  }, [setMLStatus]);

  if (!mlStatus) {
    return (
      <div className="panel space-y-2">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
          <Brain size={12} /> ML Pipeline
        </h3>
        <p className="text-slate-500 text-xs">Loading...</p>
      </div>
    );
  }

  const isReal = mlStatus.mode === "real";
  const isLoaded = mlStatus.modelLoaded;
  const unavailable = !isLoaded && !isReal;

  const modeBg = isReal ? "bg-green-900/30 border-green-800" : "bg-yellow-900/30 border-yellow-800";
  const modeText = isReal ? "text-green-400" : "text-yellow-400";
  const modeLabel = isReal ? "REAL" : "MOCK";
  const StatusIcon = unavailable ? AlertTriangle : isReal ? Activity : Cpu;
  const statusColor = unavailable ? "text-red-400" : isReal ? "text-green-400" : "text-yellow-400";
  const statusLabel = unavailable ? "UNAVAILABLE" : isReal ? "READY" : "READY (SIM)";

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Brain size={12} /> ML Pipeline
      </h3>
      <div className={`text-[11px] p-1.5 rounded border ${modeBg}`}>
        <div className={`font-bold ${modeText}`}>{modeLabel} MODE</div>
      </div>
      <div className="space-y-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-slate-400">Model</span>
          <span className="font-mono text-slate-200">{mlStatus.modelName}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Version</span>
          <span className="font-mono text-slate-200">{mlStatus.modelVersion}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Loaded</span>
          <span className={`font-mono font-bold ${isLoaded ? "text-green-400" : "text-red-400"}`}>
            {isLoaded ? "YES" : "NO"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Threshold</span>
          <span className="font-mono text-slate-200">{mlStatus.threshold}</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-[11px]">
        <StatusIcon size={12} className={statusColor} />
        <span className={`font-bold ${statusColor}`}>{statusLabel}</span>
      </div>
    </div>
  );
}
