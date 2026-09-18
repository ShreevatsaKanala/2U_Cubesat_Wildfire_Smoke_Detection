"use client";
import React from "react";
import dynamic from "next/dynamic";
import { useTelemetrySocket } from "@/lib/websocket";
import SpacecraftStatus from "@/components/SpacecraftStatus";
import HealthPanel from "@/components/HealthPanel";
import PowerPanel from "@/components/PowerPanel";
import ThermalPanel from "@/components/ThermalPanel";
import MissionControls from "@/components/MissionControls";
import FaultInjectionPanel from "@/components/FaultInjectionPanel";
import LiveTelemetry from "@/components/LiveTelemetry";
import ObservationCenter from "@/components/ObservationCenter";
import ObservationHistoryPanel from "@/components/ObservationHistoryPanel";
import MissionEventsPanel from "@/components/MissionEventsPanel";
import GroundStationPanel from "@/components/GroundStationPanel";
import GroundNetworkPanel from "@/components/GroundNetworkPanel";
import FIRMSOverlayPanel from "@/components/FIRMSOverlayPanel";
import DownlinkQueuePanel from "@/components/DownlinkQueuePanel";
import EnvironmentPanel from "@/components/EnvironmentPanel";
import SimulationClock from "@/components/SimulationClock";
import ConnectionIndicator from "@/components/ConnectionIndicator";
import AIStatusPanel from "@/components/AIStatusPanel";
import ModelComparisonPanel from "@/components/ModelComparisonPanel";
import DatasetInspectorPanel from "@/components/DatasetInspectorPanel";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

export default function MissionControl() {
  useTelemetrySocket();

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-mission-panel border-b border-mission-border px-4 py-2 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold tracking-wide text-slate-100">
            <span className="text-mission-accent">CUBESAT</span> DIGITAL TWIN
          </h1>
          <span className="text-[10px] text-slate-500 border border-mission-border rounded px-1.5 py-0.5">Phase 5</span>
        </div>
        <div className="flex items-center gap-3">
          <ConnectionIndicator />
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left sidebar - Spacecraft Status */}
        <aside className="w-64 overflow-y-auto p-2 space-y-2 border-r border-mission-border bg-mission-dark shrink-0">
          <SpacecraftStatus />
          <PowerPanel />
          <ThermalPanel />
          <HealthPanel />
        </aside>

        {/* Center - Globe */}
        <main className="flex-1 min-w-0">
          <Globe />
        </main>

        {/* Right sidebar - Operations */}
        <aside className="w-72 overflow-y-auto p-2 space-y-2 border-l border-mission-border bg-mission-dark shrink-0">
          <MissionControls />
          <ObservationCenter />
          <AIStatusPanel />
          <GroundNetworkPanel />
          <FIRMSOverlayPanel />
          <EnvironmentPanel />
          <GroundStationPanel />
          <DownlinkQueuePanel />
          <ObservationHistoryPanel />
          <ModelComparisonPanel />
          <DatasetInspectorPanel />
          <FaultInjectionPanel />
        </aside>
      </div>

      {/* Bottom - Timeline, Telemetry Log, Events */}
      <div className="border-t border-mission-border bg-mission-panel shrink-0 h-52 flex">
        <div className="flex-1 overflow-y-auto p-2">
          <LiveTelemetry />
        </div>
        <div className="border-l border-mission-border flex-1 overflow-y-auto p-2">
          <MissionEventsPanel />
        </div>
        <div className="border-l border-mission-border">
          <SimulationClock />
        </div>
      </div>
    </div>
  );
}
