"use client";
import React, { useEffect, useRef, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";

let Cesium: any = null;

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const satelliteEntityRef = useRef<any>(null);
  const trackPointsRef = useRef<any[]>([]);
  const initializedRef = useRef(false);
  const telemetry = useMissionStore((s) => s.telemetry);
  const [cesiumLoaded, setCesiumLoaded] = useState(false);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const init = async () => {
      Cesium = await import("cesium");
      (window as any).Cesium = Cesium;

      const token = process.env.NEXT_PUBLIC_CESIUM_TOKEN || "";
      if (token) {
        Cesium.Ion.defaultAccessToken = token;
      }

      if (!containerRef.current) return;

      const viewer = new Cesium.Viewer(containerRef.current, {
        animation: false,
        timeline: false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        infoBox: false,
        selectionIndicator: false,
        shadows: false,
        shouldAnimate: true,
        imageryProvider: Cesium.IonImageryProvider?.fromAssetId
          ? undefined
          : new Cesium.UrlTemplateImageryProvider({
              url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
              subdomains: ["a", "b", "c"],
            }),
      });

      try {
        const provider = await Cesium.IonImageryProvider.fromAssetId(2);
        viewer.imageryLayers.removeAll();
        viewer.imageryLayers.addImageryProvider(provider);
      } catch {}

      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(0, 20, 25000000),
        orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
      });

      const satelliteEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(0, 0, 500000),
        point: { pixelSize: 12, color: Cesium.Color.CYAN, outlineColor: Cesium.Color.WHITE, outlineWidth: 2 },
        label: { text: "2U CubeSat", font: "12px sans-serif", fillColor: Cesium.Color.WHITE, style: Cesium.LabelStyle.FILL_AND_OUTLINE, outlineWidth: 2, verticalOrigin: Cesium.VerticalOrigin.BOTTOM, pixelOffset: new Cesium.Cartesian2(0, -16) },
      });

      satelliteEntityRef.current = satelliteEntity;
      viewerRef.current = viewer;
      setCesiumLoaded(true);
    };

    init();
    return () => { viewerRef.current?.destroy(); };
  }, []);

  useEffect(() => {
    if (!viewerRef.current || !telemetry || !Cesium) return;

    const viewer = viewerRef.current;
    const pos = Cesium.Cartesian3.fromDegrees(telemetry.longitude, telemetry.latitude, telemetry.altitude_km * 1000);

    if (satelliteEntityRef.current) {
      satelliteEntityRef.current.position = pos;
    }

    trackPointsRef.current.push(pos);
    if (trackPointsRef.current.length > 500) trackPointsRef.current.shift();

    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(telemetry.longitude, telemetry.latitude, telemetry.altitude_km * 1000 + 5000000),
      orientation: { heading: 0, pitch: -Math.PI / 3, roll: 0 },
      duration: 0.5,
    });
  }, [telemetry]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {!cesiumLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-mission-dark">
          <div className="text-mission-accent text-lg">Loading Cesium...</div>
        </div>
      )}
    </div>
  );
}
