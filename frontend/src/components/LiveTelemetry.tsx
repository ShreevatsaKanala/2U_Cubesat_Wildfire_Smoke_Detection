"use client";
import React, { useRef, useEffect } from "react";
import { useMissionStore } from "@/stores/telemetryStore";

export default function LiveTelemetry() {
  const history = useMissionStore((s) => s.telemetryHistory);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.length]);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider">Live Telemetry</h3>
      <div className="max-h-64 overflow-y-auto font-mono text-xs space-y-1">
        {history.length === 0 && <p className="text-slate-500">Awaiting telemetry stream...</p>}
        {history.slice(-50).map((t, i) => (
          <div key={i} className="flex gap-2 text-slate-400">
            <span className="text-slate-600 w-12 shrink-0">#{t.packet_sequence}</span>
            <span className="text-slate-500 w-20 shrink-0">{new Date(t.timestamp).toLocaleTimeString()}</span>
            <span className="text-slate-300">{t.mission_mode}</span>
            <span className="text-slate-500">|</span>
            <span>{t.latitude.toFixed(2)}°{t.latitude >= 0 ? "N" : "S"}</span>
            <span>{t.longitude.toFixed(2)}°{t.longitude >= 0 ? "E" : "W"}</span>
            <span>{t.altitude_km.toFixed(0)}km</span>
            <span className="text-slate-500">|</span>
            <span>Bat:{t.battery_percentage.toFixed(0)}%</span>
            {t.smoke_probability !== null && (
              <>
                <span className="text-slate-500">|</span>
                <span className={t.smoke_probability > 0.6 ? "text-mission-danger" : "text-slate-300"}>Smoke:{t.smoke_probability.toFixed(3)}</span>
                {t.priority && <span className={t.priority === "CRITICAL" ? "text-mission-critical" : t.priority === "HIGH" ? "text-orange-400" : "text-slate-400"}>[{t.priority}]</span>}
              </>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
