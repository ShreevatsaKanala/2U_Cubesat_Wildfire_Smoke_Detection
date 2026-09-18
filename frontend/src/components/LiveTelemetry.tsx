"use client";
import React, { useRef, useEffect, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";

type SubsystemKey = "obc" | "camera" | "comms" | "adcs" | "thermal" | "eps";

const SUBSYSTEMS: { key: SubsystemKey; label: string; icon: string }[] = [
  { key: "obc", label: "OBC", icon: "⬡" },
  { key: "camera", label: "Camera", icon: "◉" },
  { key: "comms", label: "Comms", icon: "◈" },
  { key: "adcs", label: "ADCS", icon: "◇" },
  { key: "thermal", label: "Thermal", icon: "△" },
  { key: "eps", label: "EPS", icon: "⚡" },
];

function getStatusColor(status: string): string {
  switch (status?.toUpperCase()) {
    case "NOMINAL":
    case "OPERATIONAL":
      return "text-mission-success";
    case "WARNING":
    case "DEGRADED":
      return "text-mission-warning";
    case "CRITICAL":
    case "FAILURE":
    case "OFFLINE":
      return "text-mission-danger";
    default:
      return "text-slate-400";
  }
}

function getStatusDot(status: string): string {
  switch (status?.toUpperCase()) {
    case "NOMINAL":
    case "OPERATIONAL":
      return "bg-mission-success";
    case "WARNING":
    case "DEGRADED":
      return "bg-mission-warning";
    case "CRITICAL":
    case "FAILURE":
    case "OFFLINE":
      return "bg-mission-danger";
    default:
      return "bg-slate-600";
  }
}

function getStatusBg(status: string): string {
  switch (status?.toUpperCase()) {
    case "NOMINAL":
    case "OPERATIONAL":
      return "bg-green-900/20 border-green-800/30";
    case "WARNING":
    case "DEGRADED":
      return "bg-yellow-900/20 border-yellow-800/30";
    case "CRITICAL":
    case "FAILURE":
    case "OFFLINE":
      return "bg-red-900/20 border-red-800/30";
    default:
      return "bg-slate-800/30 border-slate-700/30";
  }
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h}h ${m}m ${s}s`;
}

export default function LiveTelemetry() {
  const history = useMissionStore((s) => s.telemetryHistory);
  const telemetry = useMissionStore((s) => s.telemetry);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [flashEntry, setFlashEntry] = useState<number | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    if (history.length > 0) {
      setFlashEntry(history.length - 1);
      const t = setTimeout(() => setFlashEntry(null), 800);
      return () => clearTimeout(t);
    }
  }, [history.length]);

  const health = telemetry?.health;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider">Live Telemetry</h3>

      {/* Subsystem Status Grid */}
      {health && (
        <div className="grid grid-cols-6 gap-1">
          {SUBSYSTEMS.map(({ key, label, icon }) => {
            const sub = health[key as keyof typeof health];
            const subHealth = sub && typeof sub === "object" && "status" in sub ? sub as { status: string; uptime_s: number } : null;
            const status = subHealth?.status ?? "UNKNOWN";
            return (
              <div key={key} className={`rounded p-1 text-center border ${getStatusBg(status)}`}>
                <div className={`w-1.5 h-1.5 rounded-full mx-auto mb-0.5 ${getStatusDot(status)}`} />
                <div className="text-[8px] text-slate-500">{icon}</div>
                <div className="text-[9px] text-slate-400">{label}</div>
                <div className={`text-[8px] font-mono font-bold ${getStatusColor(status)}`}>
                  {status.slice(0, 6)}
                </div>
                {subHealth && (
                  <div className="text-[7px] text-slate-600 font-mono">{formatUptime(subHealth.uptime_s)}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Status Bar */}
      <div className="flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Packets: <span className="text-slate-300 font-mono">{history.length}</span></span>
          {telemetry && (
            <>
              <span className="text-slate-500">Mode: <span className="text-mission-accent font-mono">{telemetry.mission_mode}</span></span>
              <span className="text-slate-500">Health: <span className={`font-mono font-bold ${
                health?.overall === "NOMINAL" || health?.overall === "OPERATIONAL" ? "text-green-400" :
                health?.overall === "WARNING" ? "text-yellow-400" :
                health?.overall === "CRITICAL" ? "text-red-400" : "text-slate-400"
              }`}>{health?.overall ?? "—"}</span></span>
            </>
          )}
        </div>
        {telemetry?.power && (
          <div className="flex items-center gap-2">
            <span className="text-slate-500">Bat: <span className={`font-mono ${telemetry.power.battery_soc > 50 ? "text-green-400" : telemetry.power.battery_soc > 20 ? "text-yellow-400" : "text-red-400"}`}>{telemetry.power.battery_soc.toFixed(0)}%</span></span>
            <span className="text-slate-500">V: <span className="font-mono text-slate-300">{telemetry.power.battery_voltage.toFixed(2)}V</span></span>
            <span className="text-slate-500">P: <span className={`font-mono ${telemetry.power.power_balance_w >= 0 ? "text-green-400" : "text-red-400"}`}>{telemetry.power.power_balance_w >= 0 ? "+" : ""}{telemetry.power.power_balance_w.toFixed(1)}W</span></span>
            {telemetry.power.eclipse && <span className="text-yellow-400 text-[9px] font-bold">ECLIPSE</span>}
          </div>
        )}
      </div>

      {/* Telemetry Log */}
      <div className="max-h-28 overflow-y-auto font-mono text-[10px] space-y-0.5 scrollbar-thin">
        {history.length === 0 && <p className="text-slate-500">Awaiting telemetry stream...</p>}
        {history.slice(-60).map((t, i) => {
          const actualIdx = history.length - 60 + i;
          const isNew = actualIdx === flashEntry;
          return (
            <div
              key={i}
              className={`flex gap-1.5 py-0.5 px-1 rounded transition-colors duration-500 ${
                isNew ? "bg-mission-accent/10" : ""
              }`}
            >
              <span className="text-slate-600 w-8 shrink-0">#{t.packet_sequence}</span>
              <span className="text-slate-500 w-14 shrink-0">{new Date(t.timestamp).toLocaleTimeString()}</span>
              <span className="text-mission-accent w-10 shrink-0">{t.mission_mode}</span>
              <span className="text-slate-600">|</span>
              <span className="text-slate-300">{t.position.latitude.toFixed(1)}°</span>
              <span className="text-slate-300">{t.position.longitude.toFixed(1)}°</span>
              <span className="text-slate-400">{t.position.altitude_km.toFixed(0)}km</span>
              <span className="text-slate-600">|</span>
              <span className={t.power.battery_soc > 50 ? "text-green-400" : t.power.battery_soc > 20 ? "text-yellow-400" : "text-red-400"}>
                Bat:{t.power.battery_soc.toFixed(0)}%
              </span>
              <span className={t.power.eclipse ? "text-yellow-400" : "text-slate-600"}>
                {t.power.eclipse ? "E" : ""}
              </span>
              {t.ai_smoke_score !== null && t.ai_smoke_score !== undefined ? (
                <>
                  <span className="text-slate-600">|</span>
                  <span className={t.ai_smoke_score > 0.6 ? "text-mission-danger" : "text-slate-300"}>AI:{t.ai_smoke_score.toFixed(3)}</span>
                  {t.ai_provider && <span className="text-slate-600">[{t.ai_provider}]</span>}
                  {t.priority && <span className={t.priority === "CRITICAL" ? "text-mission-critical" : t.priority === "HIGH" ? "text-orange-400" : "text-slate-400"}>[{t.priority}]</span>}
                </>
              ) : t.smoke_probability !== null && (
                <>
                  <span className="text-slate-600">|</span>
                  <span className={t.smoke_probability > 0.6 ? "text-mission-danger" : "text-slate-300"}>Smoke:{t.smoke_probability.toFixed(3)}</span>
                  {t.priority && <span className={t.priority === "CRITICAL" ? "text-mission-critical" : t.priority === "HIGH" ? "text-orange-400" : "text-slate-400"}>[{t.priority}]</span>}
                </>
              )}
              <span className="text-slate-700">|</span>
              <span className={`${
                t.health?.overall === "NOMINAL" || t.health?.overall === "OPERATIONAL" ? "text-green-400" :
                t.health?.overall === "WARNING" ? "text-yellow-400" :
                t.health?.overall === "CRITICAL" ? "text-red-400" : "text-slate-500"
              }`}>
                {t.health?.overall ?? "—"}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
