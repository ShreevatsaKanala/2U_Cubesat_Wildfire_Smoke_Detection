"use client";
import React from "react";
import dynamic from "next/dynamic";
import { useDemoEngine } from "@/hooks/useDemoEngine";
import MissionHeader from "@/components/MissionHeader";
import SpacecraftStatus from "@/components/SpacecraftStatus";
import PowerPanel from "@/components/PowerPanel";
import ThermalPanel from "@/components/ThermalPanel";
import ADCSPanel from "@/components/ADCSPanel";
import AIVisionPanel from "@/components/AIVisionPanel";
import ObservationCenter from "@/components/ObservationCenter";
import DownlinkQueuePanel from "@/components/DownlinkQueuePanel";
import GroundStationStrip from "@/components/GroundStationStrip";
import MissionEventsPanel from "@/components/MissionEventsPanel";
import DemoControls from "@/components/DemoControls";

const Globe = dynamic(() => import("@/components/Globe"), { ssr: false });

export default function MissionControl() {
  const {
    state,
    start,
    pause,
    reset,
    setSpeed,
    setScenario,
    injectFault,
    clearFaults,
  } = useDemoEngine();

  return (
    <div className="h-screen flex flex-col overflow-hidden scanline">
      <MissionHeader state={state} />

      <div className="flex-1 flex overflow-hidden min-h-0">
        <aside className="w-56 overflow-y-auto p-1.5 space-y-1.5 border-r border-mission-border bg-mission-dark/50 shrink-0 scrollbar-thin">
          <SpacecraftStatus state={state} />
          <PowerPanel state={state} />
          <ThermalPanel state={state} />
          <ADCSPanel state={state} />
        </aside>

        <main className="flex-1 min-w-0 relative">
          <Globe demoState={state} />
        </main>

        <aside className="w-64 overflow-y-auto p-1.5 space-y-1.5 border-l border-mission-border bg-mission-dark/50 shrink-0 scrollbar-thin">
          <AIVisionPanel state={state} />
          <ObservationCenter state={state} />
          <DownlinkQueuePanel state={state} />
        </aside>
      </div>

      <div className="border-t border-mission-border bg-mission-panel/60 backdrop-blur shrink-0">
        <div className="px-2 py-1.5">
          <GroundStationStrip state={state} />
        </div>
      </div>

      <div className="border-t border-mission-border bg-mission-panel/60 backdrop-blur shrink-0 h-36 flex">
        <div className="flex-1 overflow-y-auto p-2 scrollbar-thin">
          <MissionEventsPanel state={state} />
        </div>
        <div className="border-l border-mission-border px-3 py-1.5 flex items-center">
          <DemoControls
            state={state}
            onStart={start}
            onPause={pause}
            onReset={reset}
            onSetSpeed={setSpeed}
            onSetScenario={setScenario}
            onInjectFault={injectFault}
            onClearFaults={clearFaults}
          />
        </div>
      </div>
    </div>
  );
}
