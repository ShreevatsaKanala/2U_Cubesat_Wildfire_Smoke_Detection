"use client";
import React, { useState, useEffect, useCallback } from "react";
import type { DemoObservation } from "@/lib/demoEngine";

interface SentinelOverlayProps {
  observation: DemoObservation | null;
  onDismiss: () => void;
}

export default function SentinelObservationOverlay({ observation, onDismiss }: SentinelOverlayProps) {
  const [visible, setVisible] = useState(false);
  const [activeTab, setActiveTab] = useState<"true-color" | "ndvi" | "false-color">("true-color");
  const [sentinelData, setSentinelData] = useState<any>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    if (observation) {
      setVisible(true);
      setActiveTab("true-color");
      setSentinelData(null);
      setSearching(true);

      fetch(`/api/v1/sentinel/observe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          observation_id: observation.id,
          latitude: observation.latitude,
          longitude: observation.longitude,
          datetime: observation.timestamp,
        }),
      })
        .then((r) => r.json())
        .then((data) => {
          setSentinelData(data);
          setSearching(false);
        })
        .catch(() => {
          setSearching(false);
        });
    } else {
      setVisible(false);
    }
  }, [observation]);

  const handleDismiss = useCallback(() => {
    setVisible(false);
    setTimeout(onDismiss, 300);
  }, [onDismiss]);

  if (!observation) return null;

  return (
    <div
      className={`absolute inset-0 z-50 flex items-center justify-center transition-opacity duration-300 ${
        visible ? "opacity-100" : "opacity-0 pointer-events-none"
      }`}
      onClick={handleDismiss}
    >
      <div
        className="bg-mission-dark/95 border border-mission-accent/30 rounded-lg p-4 max-w-[480px] w-full mx-4 backdrop-blur-sm shadow-2xl shadow-mission-accent/10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-3">
          <div>
            <div className="text-[10px] font-bold text-mission-accent uppercase tracking-widest">New Payload Observation</div>
            <div className="text-sm font-mono font-bold text-slate-100 mt-0.5">{observation.id}</div>
          </div>
          <button onClick={handleDismiss} className="text-slate-500 hover:text-slate-300 text-lg leading-none">&times;</button>
        </div>

        <div className="space-y-2 mb-3">
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400 uppercase tracking-wider">SENTINEL-2 REFERENCE</span>
            <span className="text-slate-300">Level-2A</span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">Location</span>
            <span className="text-slate-200">
              {observation.latitude.toFixed(2)}&deg; {observation.latitude >= 0 ? "N" : "S"}{" "}
              {observation.longitude.toFixed(2)}&deg; {observation.longitude >= 0 ? "E" : "W"}
            </span>
          </div>
        </div>

        {sentinelData?.available && (
          <div className="space-y-2 mb-3 text-[10px] font-mono">
            <div className="flex justify-between">
              <span className="text-slate-400">ACQUIRED</span>
              <span className="text-slate-200">{sentinelData.acquisition_time || "N/A"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">CLOUD COVER</span>
              <span className="text-slate-200">{sentinelData.cloud_cover != null ? `${sentinelData.cloud_cover.toFixed(1)}%` : "N/A"}</span>
            </div>
          </div>
        )}

        <div className="relative bg-mission-panel border border-mission-border rounded h-48 flex items-center justify-center mb-3 overflow-hidden">
          {searching ? (
            <div className="text-center">
              <div className="text-[10px] text-mission-accent font-mono animate-pulse">SEARCHING SENTINEL ARCHIVE...</div>
            </div>
          ) : sentinelData?.available ? (
            <div className="text-center">
              <div className="text-[10px] text-mission-success font-mono">SENTINEL-2 SCENE FOUND</div>
              <div className="text-[9px] text-slate-500 font-mono mt-1">{sentinelData.scene_id}</div>
              {activeTab === "true-color" && sentinelData.true_color_url && (
                <img
                  src={`data:image/png;base64,${sentinelData.true_color_url}`}
                  alt="Sentinel-2 True Color"
                  className="mt-2 rounded max-h-36 mx-auto"
                />
              )}
              {activeTab === "ndvi" && sentinelData.ndvi_url && (
                <img
                  src={`data:image/png;base64,${sentinelData.ndvi_url}`}
                  alt="Sentinel-2 NDVI"
                  className="mt-2 rounded max-h-36 mx-auto"
                />
              )}
              {activeTab === "false-color" && sentinelData.false_color_url && (
                <img
                  src={`data:image/png;base64,${sentinelData.false_color_url}`}
                  alt="Sentinel-2 False Color"
                  className="mt-2 rounded max-h-36 mx-auto"
                />
              )}
            </div>
          ) : (
            <div className="text-center">
              <div className="text-[10px] text-slate-500 font-mono">
                {sentinelData?.error ? "SENTINEL UNAVAILABLE" : "IMAGERY PENDING"}
              </div>
              <div className="text-[9px] text-slate-600 font-mono mt-1">Reference imagery will appear here</div>
            </div>
          )}
        </div>

        {sentinelData?.available && (
          <div className="flex gap-1 mb-3">
            {(["true-color", "ndvi", "false-color"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 text-[9px] font-mono uppercase tracking-wider py-1.5 rounded border transition-colors ${
                  activeTab === tab
                    ? "bg-mission-accent/20 border-mission-accent/50 text-mission-accent"
                    : "border-mission-border text-slate-500 hover:text-slate-300"
                }`}
              >
                {tab === "true-color" ? "TRUE COLOR" : tab === "ndvi" ? "NDVI" : "FALSE COLOR"}
              </button>
            ))}
          </div>
        )}

        <div className="border-t border-mission-border pt-2 space-y-1">
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">AI SMOKE SCORE</span>
            <span className={`font-bold ${observation.smokeScore > 0.8 ? "text-mission-danger" : observation.smokeScore > 0.6 ? "text-mission-warning" : "text-mission-success"}`}>
              {(observation.smokeScore * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">CONFIDENCE</span>
            <span className="text-slate-200">{observation.confidence}</span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">PRIORITY</span>
            <span className={`font-bold ${observation.priority === "CRITICAL" ? "text-mission-danger" : observation.priority === "HIGH" ? "text-mission-warning" : "text-slate-200"}`}>
              {observation.priority}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
