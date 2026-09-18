"use client";
import React, { useEffect, useState, useCallback } from "react";
import { fetchHotspots } from "@/lib/api";
import { Flame, TrendingUp, AlertTriangle, Clock } from "lucide-react";

interface Hotspot {
  lat: number;
  lon: number;
  frp: number;
  confidence: string;
}

interface FIRMSOverlayPanelProps {
  onSelectDetection?: (lat: number, lon: number) => void;
}

export default function FIRMSOverlayPanel({ onSelectDetection }: FIRMSOverlayPanelProps) {
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const loadHotspots = useCallback(() => {
    setLoading(true);
    fetchHotspots()
      .then((data) => {
        setHotspots(data);
        setLastUpdate(new Date());
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadHotspots();
    const id = setInterval(loadHotspots, 60000);
    return () => clearInterval(id);
  }, [loadHotspots]);

  const highConfidence = hotspots.filter((h) => h.confidence === "high" || h.confidence === "nominal");
  const totalFrp = hotspots.reduce((sum, h) => sum + h.frp, 0);
  const maxFrp = hotspots.length > 0 ? Math.max(...hotspots.map((h) => h.frp)) : 0;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Flame size={12} /> FIRMS Fire Detection
      </h3>

      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div className="bg-slate-800/50 rounded p-1.5">
          <div className="text-slate-500 mb-0.5">Detections</div>
          <div className="font-mono text-lg font-bold text-red-400">{hotspots.length}</div>
        </div>
        <div className="bg-slate-800/50 rounded p-1.5">
          <div className="text-slate-500 mb-0.5">High Conf</div>
          <div className="font-mono text-lg font-bold text-orange-400">{highConfidence.length}</div>
        </div>
        <div className="bg-slate-800/50 rounded p-1.5">
          <div className="text-slate-500 mb-0.5">Total FRP</div>
          <div className="font-mono text-sm font-bold text-yellow-400">{totalFrp.toFixed(0)} MW</div>
        </div>
        <div className="bg-slate-800/50 rounded p-1.5">
          <div className="text-slate-500 mb-0.5">Peak FRP</div>
          <div className="font-mono text-sm font-bold text-red-400">{maxFrp.toFixed(0)} MW</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-1 text-slate-500">
          <Clock size={8} />
          <span>{lastUpdate.toLocaleTimeString()}</span>
        </div>
        <span className={`font-mono ${loading ? "text-mission-warning animate-pulse" : "text-slate-600"}`}>
          {loading ? "UPDATING..." : "OK"}
        </span>
      </div>

      <div className="space-y-1 max-h-36 overflow-y-auto">
        {hotspots.length === 0 && !loading && (
          <p className="text-slate-500 text-[10px] text-center py-2">No active detections</p>
        )}
        {hotspots.slice(0, 10).map((h, i) => (
          <button
            key={i}
            onClick={() => onSelectDetection?.(h.lat, h.lon)}
            className="w-full text-left bg-slate-800/30 hover:bg-slate-800/60 rounded p-1.5 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Flame size={8} className={h.frp > 50 ? "text-red-400" : "text-orange-400"} />
                <span className="text-[10px] font-mono text-slate-300">
                  {h.lat.toFixed(2)}°, {h.lon.toFixed(2)}°
                </span>
              </div>
              <span className={`text-[9px] font-mono font-bold ${h.frp > 50 ? "text-red-400" : "text-orange-400"}`}>
                {h.frp.toFixed(0)} MW
              </span>
            </div>
            <div className="flex items-center justify-between mt-0.5">
              <span className={`text-[9px] font-mono ${
                h.confidence === "high" || h.confidence === "nominal" ? "text-green-400" : "text-yellow-400"
              }`}>
                {h.confidence.toUpperCase()}
              </span>
              <span className="text-[9px] text-slate-600">Click to view</span>
            </div>
          </button>
        ))}
        {hotspots.length > 10 && (
          <p className="text-[9px] text-slate-600 text-center">+{hotspots.length - 10} more detections</p>
        )}
      </div>

      {hotspots.length > 0 && (
        <div className="border-t border-mission-border pt-1.5">
          <div className="flex items-center gap-1 text-[10px]">
            <AlertTriangle size={8} className="text-yellow-400" />
            <span className="text-slate-400">
              {highConfidence.length > 0 ? `${highConfidence.length} high-confidence alerts` : "All nominal"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
