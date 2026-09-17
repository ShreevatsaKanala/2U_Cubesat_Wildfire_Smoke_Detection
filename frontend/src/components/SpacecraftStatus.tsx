"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";

function StatusItem({ label, value, unit, status }: { label: string; value: string | number; unit?: string; status?: "nominal" | "warning" | "critical" }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`text-sm font-mono ${status === "warning" ? "text-mission-warning" : status === "critical" ? "text-mission-critical" : "text-slate-100"}`}>
        {typeof value === "number" ? value.toFixed(2) : value}{unit && <span className="text-slate-500 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

export default function SpacecraftStatus() {
  const t = useMissionStore((s) => s.telemetry);
  if (!t) return <div className="panel"><p className="text-slate-500 text-sm">Awaiting telemetry...</p></div>;

  const batteryStatus = t.battery_percentage > 50 ? "nominal" : t.battery_percentage > 20 ? "warning" : "critical";

  return (
    <div className="space-y-3">
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-2">Mission</h3>
        <StatusItem label="Mode" value={t.mission_mode} />
        <StatusItem label="Packet" value={`#${t.packet_sequence}`} />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-2">Navigation</h3>
        <StatusItem label="Latitude" value={t.latitude} unit="deg" />
        <StatusItem label="Longitude" value={t.longitude} unit="deg" />
        <StatusItem label="Altitude" value={t.altitude_km} unit="km" />
        <StatusItem label="Velocity" value={t.velocity_km_s} unit="km/s" />
        <StatusItem label="Heading" value={t.heading_deg} unit="deg" />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-2">Attitude</h3>
        <StatusItem label="Roll" value={t.roll_deg} unit="deg" />
        <StatusItem label="Pitch" value={t.pitch_deg} unit="deg" />
        <StatusItem label="Yaw" value={t.yaw_deg} unit="deg" />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-2">Power</h3>
        <StatusItem label="Battery" value={t.battery_percentage} unit="%" status={batteryStatus as any} />
        <StatusItem label="Voltage" value={t.battery_voltage} unit="V" />
        <StatusItem label="Generation" value={t.power_generation_w} unit="W" />
        <StatusItem label="Consumption" value={t.power_consumption_w} unit="W" />
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-2">Thermal</h3>
        {Object.entries(t.temperatures).map(([k, v]) => (
          <StatusItem key={k} label={k.charAt(0).toUpperCase() + k.slice(1)} value={v} unit="°C" />
        ))}
      </div>
      <div className="panel">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider mb-2">Subsystems</h3>
        <StatusItem label="GPS" value={t.gps_status} status={t.gps_status === "nominal" ? "nominal" : "warning"} />
        <StatusItem label="Comms" value={t.communication_status} status={t.communication_status === "nominal" ? "nominal" : "warning"} />
        <StatusItem label="Camera" value={t.camera_status} status={t.camera_status === "nominal" ? "nominal" : "warning"} />
        <StatusItem label="ML Engine" value={t.ml_status} status={t.ml_status === "nominal" ? "nominal" : "warning"} />
      </div>
    </div>
  );
}
