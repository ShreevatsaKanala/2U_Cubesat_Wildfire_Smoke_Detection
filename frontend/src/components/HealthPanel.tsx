"use client";
import React from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { Shield, Cpu, Radio, Camera, Navigation, Wifi, HardDrive } from "lucide-react";

const statusColor = (s: string) => {
  if (s === "NOMINAL") return "bg-mission-success";
  if (s === "WARNING") return "bg-mission-warning";
  return "bg-mission-danger";
};

const statusText = (s: string) => {
  if (s === "NOMINAL") return "text-mission-success";
  if (s === "WARNING") return "text-mission-warning";
  return "text-mission-danger";
};

const icons: Record<string, (props: { size?: number }) => React.ReactNode> = {
  eps: (p) => <Battery size={p.size} />,
  obc: (p) => <Cpu size={p.size} />,
  comms: (p) => <Radio size={p.size} />,
  adcs: (p) => <Navigation size={p.size} />,
  camera: (p) => <Camera size={p.size} />,
  gps: (p) => <Wifi size={p.size} />,
};

function Battery({ size: s = 10, ...props }: { size?: number } & React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect width="16" height="10" x="2" y="7" rx="2" ry="2"/><line x1="22" x2="22" y1="11" y2="13"/><line x1="6" x2="6" y1="11.01" y2="11"/>
    </svg>
  );
}

function formatUptime(s: number) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h}h ${m}m`;
}

export default function HealthPanel() {
  const t = useMissionStore((s) => s.telemetry);
  if (!t) return <div className="panel"><p className="text-slate-500 text-xs">Awaiting telemetry...</p></div>;

  const h = t.health;
  const subsystems = [
    { key: "eps", label: "EPS", iconFn: icons.eps, data: h.eps },
    { key: "obc", label: "OBC", iconFn: icons.obc, data: h.obc },
    { key: "comms", label: "COMMS", iconFn: icons.comms, data: h.comms },
    { key: "adcs", label: "ADCS", iconFn: icons.adcs, data: h.adcs },
    { key: "camera", label: "CAM", iconFn: icons.camera, data: h.camera },
    { key: "gps", label: "GPS", iconFn: icons.gps, data: h.gps },
  ];

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Shield size={12} /> Health
      </h3>
      <div className="flex items-center gap-1.5 mb-1">
        <div className={`w-2 h-2 rounded-full ${statusColor(h.overall)}`} />
        <span className={`text-[11px] font-bold uppercase ${statusText(h.overall)}`}>Overall: {h.overall}</span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {subsystems.map((sub) => (
          <div key={sub.key} className="flex items-center gap-1.5 p-1.5 rounded bg-mission-dark border border-mission-border">
            <div className={`w-1.5 h-1.5 rounded-full ${statusColor(sub.data.status)}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1">
                {sub.iconFn({ size: 10 })}
                <span className="text-[10px] font-semibold text-slate-300 uppercase">{sub.label}</span>
              </div>
              <div className="text-[9px] font-mono text-slate-500">{formatUptime(sub.data.uptime_s)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
