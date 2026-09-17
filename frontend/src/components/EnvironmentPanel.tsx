"use client";
import React, { useEffect, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchWeather, fetchAirQuality } from "@/lib/api";
import { Cloud, Wind } from "lucide-react";

export default function EnvironmentPanel() {
  const t = useMissionStore((s) => s.telemetry);
  const [weather, setWeather] = useState<{ temperature?: number; humidity?: number; description?: string } | null>(null);
  const [air, setAir] = useState<{ aqi?: number; label?: string } | null>(null);

  useEffect(() => {
    if (!t) return;
    const lat = t.position.latitude;
    const lon = t.position.longitude;
    const id = setInterval(() => {
      fetchWeather(lat, lon).then(setWeather).catch(() => {});
      fetchAirQuality(lat, lon).then(setAir).catch(() => {});
    }, 30000);
    fetchWeather(lat, lon).then(setWeather).catch(() => {});
    fetchAirQuality(lat, lon).then(setAir).catch(() => {});
    return () => clearInterval(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t?.position.latitude, t?.position.longitude]);

  if (!t) return <div className="panel"><p className="text-slate-500 text-xs">Awaiting position data...</p></div>;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Cloud size={12} /> Environment
      </h3>
      <div className="text-xs space-y-1">
        <div className="flex justify-between">
          <span className="text-slate-400">Position</span>
          <span className="font-mono text-slate-200">{t.position.latitude.toFixed(4)}°, {t.position.longitude.toFixed(4)}°</span>
        </div>
        {weather && (
          <>
            <div className="flex justify-between">
              <span className="text-slate-400">Temperature</span>
              <span className="font-mono text-slate-200">{weather.temperature?.toFixed(1) ?? "—"}°C</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Humidity</span>
              <span className="font-mono text-slate-200">{weather.humidity?.toFixed(0) ?? "—"}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Conditions</span>
              <span className="font-mono text-slate-200">{weather.description ?? "—"}</span>
            </div>
          </>
        )}
        {air && (
          <div className="flex justify-between items-center">
            <span className="text-slate-400 flex items-center gap-1"><Wind size={10} /> Air Quality</span>
            <span className={`font-mono font-bold ${air.aqi && air.aqi > 100 ? "text-mission-warning" : "text-slate-200"}`}>
              {air.aqi ?? "—"} {air.label && <span className="text-[9px] font-normal text-slate-400">{air.label}</span>}
            </span>
          </div>
        )}
        {!weather && !air && (
          <p className="text-slate-500">Loading environmental data...</p>
        )}
      </div>
    </div>
  );
}
