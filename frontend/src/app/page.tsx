"use client";
import React from "react";
import dynamic from "next/dynamic";
import { useTelemetrySocket } from "@/lib/websocket";
import SpacecraftStatus from "@/components/SpacecraftStatus";
import ObservationCenter from "@/components/ObservationCenter";
import MissionControls from "@/components/MissionControls";
import LiveTelemetry from "@/components/LiveTelemetry";
import ConnectionIndicator from "@/components/ConnectionIndicator";
import EnvironmentPanel from "@/components/EnvironmentPanel";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

export default function MissionControl() {
  useTelemetrySocket();

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-mission-panel border-b border-mission-border px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide text-slate-100">
            <span className="text-mission-accent">CUBESAT</span> DIGITAL TWIN — MISSION CONTROL
          </h1>
          <span className="text-xs text-slate-500">2U Wildfire Smoke Detection</span>
        </div>
        <div className="flex items-center gap-4">
          <ConnectionIndicator />
          <span className="text-xs text-slate-600">Phase 1 v0.1.0</span>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar - Status */}
        <aside className="w-72 overflow-y-auto p-3 space-y-3 border-r border-mission-border bg-mission-dark">
          <SpacecraftStatus />
          <MissionControls />
        </aside>

        {/* Center - Globe */}
        <main className="flex-1 relative">
          <Globe />
          <div className="absolute bottom-4 left-4 right-4">
            <LiveTelemetry />
          </div>
        </main>

        {/* Right sidebar - Observations & Environment */}
        <aside className="w-80 overflow-y-auto p-3 space-y-3 border-l border-mission-border bg-mission-dark">
          <ObservationCenter />
          <EnvironmentPanel />
        </aside>
      </div>
    </div>
  );
}
