"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchGroundStationStatus } from "@/lib/api";
import { Radio, MapPin, Activity, Clock, Signal } from "lucide-react";

interface Station {
  name: string;
  lat: number;
  lon: number;
  color: string;
  status: "active" | "standby";
}

const STATIONS: Station[] = [
  { name: "Boulder CO", lat: 40.015, lon: -105.2705, color: "bg-mission-success", status: "active" },
  { name: "Fairbanks AK", lat: 64.8378, lon: -147.7164, color: "bg-blue-400", status: "standby" },
  { name: "Svalbard", lat: 78.2232, lon: 15.6267, color: "bg-purple-400", status: "standby" },
  { name: "Singapore", lat: 1.3521, lon: 103.8198, color: "bg-yellow-400", status: "standby" },
  { name: "Punta Arenas", lat: -53.1638, lon: -70.9171, color: "bg-red-400", status: "standby" },
];

export default function GroundNetworkPanel() {
  const telemetry = useMissionStore((s) => s.telemetry);
  const [stationStatuses, setStationStatuses] = useState<Record<string, { visible: boolean; distance: number; nextPass: number; elevation: number; azimuth: number }>>({});

  const loadStatuses = useCallback(() => {
    fetchGroundStationStatus().then((gs) => {
      const visible = gs.is_visible;
      setStationStatuses((prev) => {
        const updated = { ...prev };
        STATIONS.forEach((s, i) => {
          updated[s.name] = {
            visible: i === 0 ? visible : false,
            distance: gs.distance_km + i * 500,
            nextPass: gs.next_pass_s + i * 300,
            elevation: i === 0 ? gs.elevation_deg : Math.max(0, gs.elevation_deg - 15 - i * 10),
            azimuth: i === 0 ? gs.azimuth_deg : (gs.azimuth_deg + i * 45) % 360,
          };
        });
        return updated;
      });
    }).catch(() => {});
  }, []);

  useEffect(() => {
    loadStatuses();
    const id = setInterval(loadStatuses, 5000);
    return () => clearInterval(id);
  }, [loadStatuses]);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Radio size={12} /> Ground Network
      </h3>
      <div className="space-y-2">
        {STATIONS.map((station) => {
          const status = stationStatuses[station.name];
          const isVisible = status?.visible ?? false;
          const nextPass = status?.nextPass ?? 0;
          const dataRate = isVisible ? (2.4 + Math.random() * 0.5).toFixed(1) : "—";

          return (
            <div key={station.name} className="bg-slate-800/40 rounded p-2 space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <MapPin size={10} className={station.color.replace("bg-", "text-")} />
                  <span className="text-[11px] font-semibold text-slate-200">{station.name}</span>
                </div>
                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${station.status === "active" ? "bg-green-900/40 text-green-400" : "bg-slate-700 text-slate-500"}`}>
                  {station.status.toUpperCase()}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-2 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-slate-500">Visibility</span>
                  <span className={`font-mono font-bold ${isVisible ? "text-green-400" : "text-slate-500"}`}>
                    {isVisible ? "IN VIEW" : "OUT"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Data Rate</span>
                  <span className="font-mono text-slate-300">{dataRate} Mbps</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Elevation</span>
                  <span className="font-mono text-slate-300">{(status?.elevation ?? 0).toFixed(1)}°</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Azimuth</span>
                  <span className="font-mono text-slate-300">{(status?.azimuth ?? 0).toFixed(0)}°</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-[10px]">
                  <Signal size={8} className={isVisible ? "text-green-400" : "text-slate-600"} />
                  <span className={`font-mono ${isVisible ? "text-green-400" : "text-slate-500"}`}>
                    {isVisible ? "LINK ACTIVE" : "NO LINK"}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-[10px]">
                  <Clock size={8} className="text-slate-500" />
                  <span className="font-mono text-slate-400">
                    {nextPass > 0 ? `${Math.floor(nextPass / 60)}m ${Math.floor(nextPass % 60)}s` : "NOW"}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
