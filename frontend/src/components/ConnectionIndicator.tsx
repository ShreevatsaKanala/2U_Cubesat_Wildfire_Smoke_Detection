"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";

export default function ConnectionIndicator() {
  const connected = useMissionStore((s) => s.connected);
  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${connected ? "bg-mission-success animate-pulse" : "bg-mission-danger"}`} />
      <span className="text-xs text-slate-400">{connected ? "CONNECTED" : "DISCONNECTED"}</span>
    </div>
  );
}
