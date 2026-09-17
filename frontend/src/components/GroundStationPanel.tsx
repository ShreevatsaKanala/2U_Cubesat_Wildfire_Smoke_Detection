"use client";
import React, { useEffect, useCallback } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchGroundStationStatus } from "@/lib/api";
import { Radio } from "lucide-react";

export default function GroundStationPanel() {
  const { groundStation, setGroundStation } = useMissionStore();

  const load = useCallback(() => {
    fetchGroundStationStatus().then(setGroundStation).catch(() => {});
  }, [setGroundStation]);

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Radio size={12} /> Ground Station
      </h3>
      {!groundStation ? (
        <p className="text-slate-500 text-xs">Loading...</p>
      ) : (
        <div className="space-y-1 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-400">Distance</span>
            <span className="font-mono text-slate-200">{groundStation.distance_km.toFixed(1)} km</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400">Visibility</span>
            <span className={`flex items-center gap-1 font-mono font-bold ${groundStation.is_visible ? "text-mission-success" : "text-slate-500"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${groundStation.is_visible ? "bg-mission-success animate-pulse" : "bg-slate-600"}`} />
              {groundStation.is_visible ? "IN VIEW" : "OUT OF VIEW"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Elevation</span>
            <span className="font-mono text-slate-200">{groundStation.elevation_deg.toFixed(1)}°</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Azimuth</span>
            <span className="font-mono text-slate-200">{groundStation.azimuth_deg.toFixed(1)}°</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Next Pass</span>
            <span className={`font-mono font-bold ${groundStation.next_pass_s < 60 ? "text-mission-success" : "text-slate-200"}`}>
              {groundStation.next_pass_s > 0 ? `${Math.floor(groundStation.next_pass_s / 60)}m ${Math.floor(groundStation.next_pass_s % 60)}s` : "NOW"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
