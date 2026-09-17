"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { Satellite, Navigation, Radio, Gauge } from "lucide-react";

function StatusItem({ label, value, unit, status }: { label: string; value: string | number; unit?: string; status?: "nominal" | "warning" | "critical" }) {
  return (
    <div className="flex justify-between items-center py-0.5">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-xs font-mono ${status === "warning" ? "text-mission-warning" : status === "critical" ? "text-mission-critical" : "text-slate-100"}`}>
        {typeof value === "number" ? value.toFixed(2) : value}{unit && <span className="text-slate-500 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function SpacecraftStatus() {
  const t = useMissionStore((s) => s.telemetry);
  if (!t) return <div className="panel"><p className="text-slate-500 text-xs">Awaiting telemetry...</p></div>;

  const battStatus = t.power.battery_soc > 50 ? "nominal" : t.power.battery_soc > 20 ? "warning" : "critical";

  return (
    <div className="space-y-2">
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <Satellite size={12} /> Mission
        </h3>
        <StatusItem label="Mode" value={t.mission_mode} />
        <StatusItem label="Packet" value={`#${t.packet_sequence}`} />
        <StatusItem label="SC ID" value={t.spacecraft_id} />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <Navigation size={12} /> Navigation
        </h3>
        <StatusItem label="Latitude" value={t.position.latitude} unit="deg" />
        <StatusItem label="Longitude" value={t.position.longitude} unit="deg" />
        <StatusItem label="Altitude" value={t.position.altitude_km} unit="km" />
        <StatusItem label="Velocity" value={t.position.velocity_km_s} unit="km/s" />
        <StatusItem label="Heading" value={t.position.heading_deg} unit="deg" />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <Radio size={12} /> Attitude
        </h3>
        <StatusItem label="Roll" value={t.attitude.roll_deg} unit="deg" />
        <StatusItem label="Pitch" value={t.attitude.pitch_deg} unit="deg" />
        <StatusItem label="Yaw" value={t.attitude.yaw_deg} unit="deg" />
        <StatusItem label="Mode" value={t.attitude.attitude_mode} />
        <StatusItem label="Pointing err" value={t.attitude.pointing_error_deg} unit="deg" />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-1 flex items-center gap-1.5">
          <Gauge size={12} /> Subsystems
        </h3>
        <StatusItem label="GPS" value={t.health.gps.status} status={t.health.gps.status === "NOMINAL" ? "nominal" : t.health.gps.status === "WARNING" ? "warning" : "critical"} />
        <StatusItem label="Comms" value={t.health.comms.status} status={t.health.comms.status === "NOMINAL" ? "nominal" : t.health.comms.status === "WARNING" ? "warning" : "critical"} />
        <StatusItem label="Camera" value={t.health.camera.status} status={t.health.camera.status === "NOMINAL" ? "nominal" : t.health.camera.status === "WARNING" ? "warning" : "critical"} />
        <StatusItem label="ADCS" value={t.health.adcs.status} status={t.health.adcs.status === "NOMINAL" ? "nominal" : t.health.adcs.status === "WARNING" ? "warning" : "critical"} />
        <StatusItem label="Overall" value={t.health.overall} status={t.health.overall === "NOMINAL" ? "nominal" : t.health.overall === "WARNING" ? "warning" : "critical"} />
      </div>
    </div>
  );
}
