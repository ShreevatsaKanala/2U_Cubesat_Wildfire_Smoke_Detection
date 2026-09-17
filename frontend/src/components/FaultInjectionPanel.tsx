"use client";
import React, { useEffect, useCallback } from "react";
import { useMissionStore, type Faults } from "@/stores/telemetryStore";
import { fetchFaults, injectFaults, clearFaults } from "@/lib/api";
import { AlertTriangle, ShieldAlert, ShieldOff } from "lucide-react";

const faultLabels: { key: keyof Faults; label: string }[] = [
  { key: "battery_low", label: "Battery Low" },
  { key: "camera_failure", label: "Camera Failure" },
  { key: "adcs_failure", label: "ADCS Failure" },
  { key: "comms_failure", label: "Comms Failure" },
  { key: "eclipse_stuck", label: "Eclipse Stuck" },
];

export default function FaultInjectionPanel() {
  const { faults, setFaults } = useMissionStore();

  const loadFaults = useCallback(() => {
    fetchFaults().then(setFaults).catch(() => {});
  }, [setFaults]);

  useEffect(() => {
    loadFaults();
  }, [loadFaults]);

  const handleToggle = async (key: keyof Faults) => {
    const updated = await injectFaults({ [key]: !faults[key] });
    setFaults(updated);
  };

  const handleClear = async () => {
    const updated = await clearFaults();
    setFaults(updated);
  };

  const anyActive = Object.values(faults).some(Boolean);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <AlertTriangle size={12} /> Fault Injection
      </h3>
      <div className="space-y-1">
        {faultLabels.map(({ key, label }) => (
          <button key={key} onClick={() => handleToggle(key)}
            className="w-full flex items-center justify-between px-2 py-1.5 rounded text-[11px] transition-colors bg-mission-dark border border-mission-border hover:border-slate-600">
            <span className="text-slate-300">{label}</span>
            <div className={`w-7 h-4 rounded-full transition-colors ${faults[key] ? "bg-mission-danger" : "bg-slate-700"} relative`}>
              <div className={`w-3 h-3 rounded-full absolute top-0.5 transition-all ${faults[key] ? "left-3.5 bg-white" : "left-0.5 bg-slate-400"}`} />
            </div>
          </button>
        ))}
      </div>
      {anyActive && (
        <button onClick={handleClear}
          className="w-full flex items-center justify-center gap-1 px-3 py-1.5 bg-mission-danger/20 hover:bg-mission-danger/30 border border-mission-danger/50 text-mission-danger text-[11px] font-medium rounded transition-colors">
          <ShieldOff size={10} /> Clear All Faults
        </button>
      )}
    </div>
  );
}
