"use client";
import React from "react";
import type { DemoState } from "@/lib/demoEngine";

interface SpacecraftStatusProps {
  state: DemoState | null;
}

const STATUS_COLORS: Record<string, string> = {
  NOMINAL: "bg-mission-success",
  ACTIVE: "bg-mission-success",
  LINKED: "bg-mission-success",
  LOCKED: "bg-mission-success",
  READY: "bg-mission-success",
  ONLINE: "bg-mission-success",
  NADIR: "bg-mission-success",
  WARNING: "bg-mission-warning",
  STANDBY: "bg-slate-500",
  OFFLINE: "bg-mission-danger",
};

const STATUS_TEXT_COLORS: Record<string, string> = {
  NOMINAL: "text-mission-success",
  ACTIVE: "text-mission-success",
  LINKED: "text-mission-success",
  LOCKED: "text-mission-success",
  READY: "text-mission-success",
  ONLINE: "text-mission-success",
  NADIR: "text-mission-success",
  WARNING: "text-mission-warning",
  STANDBY: "text-slate-400",
  OFFLINE: "text-mission-danger",
};

function LED({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? "bg-slate-600";
  const isAnimating = status !== "STANDBY" && status !== "OFFLINE";
  return (
    <div
      className={`w-1.5 h-1.5 rounded-full shrink-0 ${color} ${
        isAnimating ? "animate-pulse" : ""
      }`}
    />
  );
}

function StatusRow({ label, status }: { label: string; status: string }) {
  const textColor = STATUS_TEXT_COLORS[status] ?? "text-slate-400";
  return (
    <div className="flex items-center justify-between py-0.5">
      <div className="flex items-center gap-1.5">
        <LED status={status} />
        <span className="text-[10px] text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <span className={`text-[10px] font-mono font-bold ${textColor}`}>{status}</span>
    </div>
  );
}

export default function SpacecraftStatus({ state }: SpacecraftStatusProps) {
  const health = state?.health;

  return (
    <div className="panel space-y-1">
      <h3 className="text-[10px] font-semibold text-mission-accent uppercase tracking-widest mb-1.5">
        Spacecraft Status
      </h3>
      {health ? (
        <div className="space-y-0.5">
          <StatusRow label="OBC" status={health.obc} />
          <StatusRow label="CAMERA" status={health.camera} />
          <StatusRow label="ADCS" status={health.adcs} />
          <StatusRow label="EPS" status={health.eps} />
          <StatusRow label="THERMAL" status={health.thermal} />
          <StatusRow label="COMMS" status={health.comms} />
          <StatusRow label="GPS" status={health.gps} />
          <StatusRow label="AI" status={health.ai} />
        </div>
      ) : (
        <div className="text-[10px] text-slate-500 font-mono">INITIALIZING...</div>
      )}
    </div>
  );
}
