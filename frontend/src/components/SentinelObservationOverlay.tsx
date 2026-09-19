"use client";
import React, { useState, useEffect, useCallback, useRef } from "react";
import type { DemoObservation } from "@/lib/demoEngine";

type ImageTab = "true-color" | "ndvi" | "false-color";
type SearchPhase = "idle" | "searching" | "found" | "error";

interface SentinelOverlayProps {
  observation: DemoObservation | null;
  onDismiss: () => void;
}

export default function SentinelObservationOverlay({
  observation,
  onDismiss,
}: SentinelOverlayProps) {
  const [visible, setVisible] = useState(false);
  const [activeTab, setActiveTab] = useState<ImageTab>("true-color");
  const [phase, setPhase] = useState<SearchPhase>("idle");
  const [sceneMeta, setSceneMeta] = useState<{
    scene_id?: string;
    acquisition_time?: string;
    cloud_cover?: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [imageUrls, setImageUrls] = useState<Partial<Record<ImageTab, string>>>({});
  const [loadingImage, setLoadingImage] = useState<ImageTab | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);
  const obsIdRef = useRef<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      Object.values(imageUrls).forEach((url) => {
        if (url) URL.revokeObjectURL(url);
      });
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchImage = useCallback(
    async (product: ImageTab, obs: DemoObservation) => {
      if (imageUrls[product]) return;
      setLoadingImage(product);

      try {
        const res = await fetch(
          `/api/v1/sentinel/observation/${obs.id}/image/${product}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              latitude: obs.latitude,
              longitude: obs.longitude,
              datetime: obs.timestamp,
            }),
          }
        );

        if (!mountedRef.current) return;
        if (!res.ok) {
          setLoadingImage(null);
          return;
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);

        if (!mountedRef.current) {
          URL.revokeObjectURL(url);
          return;
        }

        setImageUrls((prev) => ({ ...prev, [product]: url }));
        setLoadingImage(null);
      } catch {
        if (mountedRef.current) setLoadingImage(null);
      }
    },
    [imageUrls]
  );

  const handleTabClick = useCallback(
    (tab: ImageTab) => {
      setActiveTab(tab);
      if (observation && sceneMeta && !imageUrls[tab]) {
        fetchImage(tab, observation);
      }
    },
    [observation, sceneMeta, imageUrls, fetchImage]
  );

  useEffect(() => {
    // Cancel any in-flight requests from previous observation
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    if (!observation) return;

    // New observation
    obsIdRef.current = observation.id;

    const controller = new AbortController();
    abortRef.current = controller;
    let cancelled = false;

    const search = async () => {
      setVisible(true);
      setPhase("searching");
      setSceneMeta(null);
      setError(null);
      setImageUrls({});
      setActiveTab("true-color");
      setLoadingImage(null);

      try {
        const res = await fetch(`/api/v1/sentinel/observe`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            observation_id: observation.id,
            latitude: observation.latitude,
            longitude: observation.longitude,
            datetime: observation.timestamp,
          }),
          signal: controller.signal,
        });

        if (cancelled || !mountedRef.current) return;
        if (obsIdRef.current !== observation.id) return;

        const data = await res.json();

        if (cancelled || !mountedRef.current) return;

        if (data.available) {
          setSceneMeta({
            scene_id: data.scene_id,
            acquisition_time: data.acquisition_time,
            cloud_cover: data.cloud_cover,
          });
          setPhase("found");
          // Auto-fetch true-color immediately
          fetchImage("true-color", observation);
        } else {
          setError(data.error || "Sentinel unavailable");
          setPhase("error");
        }
      } catch (err: unknown) {
        if (controller.signal.aborted || cancelled || !mountedRef.current) return;
        const msg = err instanceof Error ? err.name : "Unknown";
        setError(msg === "AbortError" ? "Search cancelled" : "Connection failed");
        setPhase("error");
      }
    };

    search();

    return () => {
      cancelled = true;
      controller.abort();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [observation?.id]);

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
        {/* Header */}
        <div className="flex justify-between items-start mb-3">
          <div>
            <div className="text-[10px] font-bold text-mission-accent uppercase tracking-widest">
              New Payload Observation
            </div>
            <div className="text-sm font-mono font-bold text-slate-100 mt-0.5">
              {observation.id}
            </div>
          </div>
          <button
            onClick={handleDismiss}
            className="text-slate-500 hover:text-slate-300 text-lg leading-none"
          >
            &times;
          </button>
        </div>

        {/* Sentinel search status */}
        <div className="flex justify-between text-[10px] font-mono mb-2">
          <span className="text-slate-400 uppercase tracking-wider">
            SENTINEL-2 REFERENCE
          </span>
          <span
            className={
              phase === "found"
                ? "text-green-400"
                : phase === "error"
                  ? "text-red-400"
                  : "text-yellow-400 animate-pulse"
            }
          >
            {phase === "searching"
              ? "SEARCHING..."
              : phase === "found"
                ? "CONNECTED"
                : phase === "error"
                  ? "UNAVAILABLE"
                  : "IDLE"}
          </span>
        </div>

        {/* Metadata */}
        <div className="space-y-2 mb-3">
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">Location</span>
            <span className="text-slate-200">
              {observation.latitude.toFixed(2)}&deg;{" "}
              {observation.latitude >= 0 ? "N" : "S"}{" "}
              {observation.longitude.toFixed(2)}&deg;{" "}
              {observation.longitude >= 0 ? "E" : "W"}
            </span>
          </div>
          {sceneMeta && (
            <>
              <div className="flex justify-between text-[10px] font-mono">
                <span className="text-slate-400">ACQUIRED</span>
                <span className="text-slate-200">
                  {sceneMeta.acquisition_time || "N/A"}
                </span>
              </div>
              <div className="flex justify-between text-[10px] font-mono">
                <span className="text-slate-400">CLOUD COVER</span>
                <span className="text-slate-200">
                  {sceneMeta.cloud_cover != null
                    ? `${sceneMeta.cloud_cover.toFixed(1)}%`
                    : "N/A"}
                </span>
              </div>
            </>
          )}
        </div>

        {/* Image area */}
        <div className="relative bg-mission-panel border border-mission-border rounded h-48 flex items-center justify-center mb-3 overflow-hidden">
          {phase === "searching" && (
            <div className="text-center">
              <div className="text-[10px] text-mission-accent font-mono animate-pulse">
                SEARCHING SENTINEL ARCHIVE...
              </div>
            </div>
          )}

          {phase === "found" && imageUrls[activeTab] && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={imageUrls[activeTab]}
              alt={`Sentinel-2 ${activeTab}`}
              className="max-h-44 max-w-full object-contain rounded"
            />
          )}

          {phase === "found" && !imageUrls[activeTab] && (
            <div className="text-center">
              <div className="text-[10px] text-mission-accent font-mono animate-pulse">
                {loadingImage === activeTab
                  ? `LOADING ${activeTab.toUpperCase().replace("-", " ")}...`
                  : "SENTINEL-2 SCENE FOUND"}
              </div>
              <div className="text-[9px] text-slate-500 font-mono mt-1">
                {sceneMeta?.scene_id}
              </div>
            </div>
          )}

          {phase === "error" && (
            <div className="text-center">
              <div className="text-[10px] text-red-400 font-mono">
                SENTINEL REFERENCE UNAVAILABLE
              </div>
              <div className="text-[9px] text-slate-600 font-mono mt-1">
                {error}
              </div>
            </div>
          )}
        </div>

        {/* Tabs */}
        {phase === "found" && (
          <div className="flex gap-1 mb-3">
            {(["true-color", "ndvi", "false-color"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => handleTabClick(tab)}
                className={`flex-1 text-[9px] font-mono uppercase tracking-wider py-1.5 rounded border transition-colors ${
                  activeTab === tab
                    ? "bg-mission-accent/20 border-mission-accent/50 text-mission-accent"
                    : "border-mission-border text-slate-500 hover:text-slate-300"
                }`}
              >
                {tab === "true-color"
                  ? "TRUE COLOR"
                  : tab === "ndvi"
                    ? "NDVI"
                    : "FALSE COLOR"}
                {loadingImage === tab && " ..."}
              </button>
            ))}
          </div>
        )}

        {/* AI results */}
        <div className="border-t border-mission-border pt-2 space-y-1">
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">AI SMOKE SCORE</span>
            <span
              className={`font-bold ${
                observation.smokeScore > 0.8
                  ? "text-mission-danger"
                  : observation.smokeScore > 0.6
                    ? "text-mission-warning"
                    : "text-mission-success"
              }`}
            >
              {(observation.smokeScore * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">CONFIDENCE</span>
            <span className="text-slate-200">{observation.confidence}</span>
          </div>
          <div className="flex justify-between text-[10px] font-mono">
            <span className="text-slate-400">PRIORITY</span>
            <span
              className={`font-bold ${
                observation.priority === "CRITICAL"
                  ? "text-mission-danger"
                  : observation.priority === "HIGH"
                    ? "text-mission-warning"
                    : "text-slate-200"
              }`}
            >
              {observation.priority}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
