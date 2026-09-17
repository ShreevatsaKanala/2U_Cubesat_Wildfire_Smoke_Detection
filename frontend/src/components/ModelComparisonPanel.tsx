"use client";
import React, { useEffect } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchMLModels } from "@/lib/api";
import { BarChart3 } from "lucide-react";

export default function ModelComparisonPanel() {
  const mlModels = useMissionStore((s) => s.mlModels);
  const setMLModels = useMissionStore((s) => s.setMLModels);

  useEffect(() => {
    fetchMLModels()
      .then((r) => setMLModels(r.models))
      .catch(() => {});
  }, [setMLModels]);

  const bestIdx = mlModels.reduce(
    (best, m, i) => (m.f1 > mlModels[best].f1 ? i : best),
    0,
  );

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <BarChart3 size={12} /> Model Evaluation
      </h3>
      {mlModels.length === 0 ? (
        <p className="text-slate-500 text-xs">No model data</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[10px]">
            <thead>
              <tr className="text-slate-400 border-b border-mission-border">
                <th className="text-left py-1 font-medium">Model</th>
                <th className="text-right py-1 font-medium">Params</th>
                <th className="text-right py-1 font-medium">Size</th>
                <th className="text-right py-1 font-medium">Prec</th>
                <th className="text-right py-1 font-medium">Rec</th>
                <th className="text-right py-1 font-medium">F1</th>
                <th className="text-right py-1 font-medium">Lat</th>
              </tr>
            </thead>
            <tbody>
              {mlModels.map((m, i) => (
                <tr
                  key={m.name}
                  className={`border-b border-mission-border/50 ${
                    i === bestIdx ? "bg-mission-accent/10" : ""
                  }`}
                >
                  <td className="py-1 text-slate-200 font-medium whitespace-nowrap">
                    {m.name}
                    {i === bestIdx && (
                      <span className="ml-1 text-[8px] text-mission-accent">BEST</span>
                    )}
                  </td>
                  <td className="py-1 text-right font-mono text-slate-300">{m.params_m}M</td>
                  <td className="py-1 text-right font-mono text-slate-300">{m.size_mb}MB</td>
                  <td className="py-1 text-right font-mono text-slate-300">{m.precision.toFixed(3)}</td>
                  <td className="py-1 text-right font-mono text-slate-300">{m.recall.toFixed(3)}</td>
                  <td className="py-1 text-right font-mono text-slate-300">{m.f1.toFixed(3)}</td>
                  <td className="py-1 text-right font-mono text-slate-300">{m.latency_ms.toFixed(0)}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
