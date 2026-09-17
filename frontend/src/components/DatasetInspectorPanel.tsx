"use client";
import React, { useEffect } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchDatasetManifest, fetchDatasetStats } from "@/lib/api";
import { Database } from "lucide-react";

export default function DatasetInspectorPanel() {
  const manifest = useMissionStore((s) => s.datasetManifest);
  const stats = useMissionStore((s) => s.datasetStats);
  const setManifest = useMissionStore((s) => s.setDatasetManifest);
  const setStats = useMissionStore((s) => s.setDatasetStats);

  useEffect(() => {
    fetchDatasetManifest().then(setManifest).catch(() => {});
    fetchDatasetStats().then(setStats).catch(() => {});
  }, [setManifest, setStats]);

  const classCounts = stats?.class_counts ?? {};
  const maxCount = Math.max(...Object.values(classCounts), 1);

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Database size={12} /> Dataset
      </h3>
      {!manifest && !stats ? (
        <p className="text-slate-500 text-xs">Loading...</p>
      ) : (
        <div className="space-y-2 text-[11px]">
          {manifest && (
            <>
              <div className="flex justify-between">
                <span className="text-slate-400">Name</span>
                <span className="font-mono text-slate-200">{manifest.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Source</span>
                <span className="font-mono text-slate-200 truncate ml-2">{manifest.source}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">License</span>
                <span className="font-mono text-slate-200">{manifest.license}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Total</span>
                <span className="font-mono text-slate-200">{manifest.total_images.toLocaleString()}</span>
              </div>
            </>
          )}
          {stats?.splits && (
            <div className="flex gap-2">
              <div className="flex-1 text-center">
                <div className="text-[9px] text-slate-500">Train</div>
                <div className="font-mono text-slate-200">{stats.splits.train.toLocaleString()}</div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-[9px] text-slate-500">Val</div>
                <div className="font-mono text-slate-200">{stats.splits.val.toLocaleString()}</div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-[9px] text-slate-500">Test</div>
                <div className="font-mono text-slate-200">{stats.splits.test.toLocaleString()}</div>
              </div>
            </div>
          )}
          {stats?.dimensions && (
            <div className="flex justify-between">
              <span className="text-slate-400">Dimensions</span>
              <span className="font-mono text-slate-200">
                {stats.dimensions.width}x{stats.dimensions.height}x{stats.dimensions.channels}
              </span>
            </div>
          )}
          {Object.keys(classCounts).length > 0 && (
            <div className="space-y-1">
              <div className="text-[9px] text-slate-500 uppercase">Class Distribution</div>
              {Object.entries(classCounts).map(([cls, count]) => (
                <div key={cls} className="space-y-0.5">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-slate-300">{cls}</span>
                    <span className="font-mono text-slate-400">{count.toLocaleString()}</span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-mission-accent rounded-full"
                      style={{ width: `${(count / maxCount) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
