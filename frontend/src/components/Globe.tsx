"use client";
import React, { useEffect, useRef, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchHotspots } from "@/lib/api";

let Cesium: typeof import("cesium") | null = null;

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<InstanceType<typeof import("cesium").Viewer> | null>(null);
  const satelliteEntityRef = useRef<any>(null);
  const groundTrackRef = useRef<any>(null);
  const orbitPathRef = useRef<any>(null);
  const footprintRef = useRef<any>(null);
  const hotspotsEntitiesRef = useRef<any[]>([]);
  const trackPointsRef = useRef<import("cesium").Cartesian3[]>([]);
  const prevCamPosRef = useRef<import("cesium").Cartesian3 | null>(null);
  const initializedRef = useRef(false);

  const telemetry = useMissionStore((s) => s.telemetry);
  const globeView = useMissionStore((s) => s.globeView);
  const cameraMode = useMissionStore((s) => s.cameraMode);
  const [cesiumLoaded, setCesiumLoaded] = useState(false);
  const [hotspots, setHotspots] = useState<{ lat: number; lon: number; frp: number; confidence: string }[]>([]);

  useEffect(() => {
    fetchHotspots().then(setHotspots).catch(() => {});
    const id = setInterval(() => {
      fetchHotspots().then(setHotspots).catch(() => {});
    }, 60000);
    return () => clearInterval(id);
  }, []);

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
        requestRenderMode: false,
        maximumRenderTimeChange: Infinity,
      });

      try {
        const provider = await Cesium.IonImageryProvider.fromAssetId(2);
        viewer.imageryLayers.removeAll();
        viewer.imageryLayers.addImageryProvider(provider);
      } catch {
        // fallback imagery
      }

      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(0, 20, 25000000),
        orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
      });

      const satelliteEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(0, 0, 500000),
        point: { pixelSize: 10, color: Cesium.Color.CYAN, outlineColor: Cesium.Color.WHITE, outlineWidth: 2 },
        label: {
          text: "2U CubeSat",
          font: "11px monospace",
          fillColor: Cesium.Color.WHITE,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 2,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -14),
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString("#111827cc"),
        },
      });

      const groundTrack = viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => trackPointsRef.current, false),
          width: 2,
          material: new Cesium.PolylineGlowMaterialProperty({ glowPower: 0.1, color: Cesium.Color.CYAN }),
        },
      });

      const orbitPath = viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => {
            if (!Cesium || !telemetry) return [];
            return computeOrbitPath(telemetry.position.latitude, telemetry.position.longitude, telemetry.position.altitude_km);
          }, false),
          width: 1.5,
          material: new Cesium.PolylineDashMaterialProperty({ color: Cesium.Color.CYAN.withAlpha(0.3), dashLength: 16 }),
        },
      });

      const footprint = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(0, 0, 0),
        polygon: {
          hierarchy: new Cesium.CallbackProperty(() => {
            if (!Cesium || !telemetry) return undefined;
            return computeCameraFootprint(telemetry.position.latitude, telemetry.position.longitude, telemetry.position.altitude_km);
          }, false),
          material: Cesium.Color.YELLOW.withAlpha(0.15),
          outline: true,
          outlineColor: Cesium.Color.YELLOW.withAlpha(0.4),
        },
      });

      satelliteEntityRef.current = satelliteEntity;
      groundTrackRef.current = groundTrack;
      orbitPathRef.current = orbitPath;
      footprintRef.current = footprint;
      viewerRef.current = viewer;
      setCesiumLoaded(true);
    };

    init();
    return () => {
      (viewerRef.current as any)?.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!viewerRef.current || !telemetry || !Cesium) return;

    const viewer = viewerRef.current;
    const pos = Cesium.Cartesian3.fromDegrees(
      telemetry.position.longitude,
      telemetry.position.latitude,
      telemetry.position.altitude_km * 1000
    );

    if (satelliteEntityRef.current) {
      satelliteEntityRef.current.position = pos;
    }

    trackPointsRef.current.push(pos);
    if (trackPointsRef.current.length > 200) trackPointsRef.current.shift();

    if (globeView === "follow" || globeView === "top-down") {
      const distance = globeView === "top-down" ? telemetry.position.altitude_km * 1000 + 2000000 : telemetry.position.altitude_km * 1000 + 5000000;
      const pitch = globeView === "top-down" ? -Math.PI / 2 : -Math.PI / 3;
      viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          telemetry.position.longitude,
          telemetry.position.latitude,
          distance
        ),
        orientation: { heading: 0, pitch, roll: 0 },
        duration: 0.3,
      });
    }
  }, [telemetry, globeView]);

  useEffect(() => {
    if (!viewerRef.current || !Cesium) return;
    const C = Cesium;
    const viewer = viewerRef.current;

    hotspotsEntitiesRef.current.forEach((e) => viewer.entities.remove(e));
    hotspotsEntitiesRef.current = [];

    hotspots.forEach((h) => {
      const entity = viewer.entities.add({
        position: C.Cartesian3.fromDegrees(h.lon, h.lat, 0),
        point: {
          pixelSize: Math.min(4 + h.frp / 10, 10),
          color: C.Color.RED.withAlpha(0.7),
          outlineColor: C.Color.ORANGE,
          outlineWidth: 1,
          heightReference: C.HeightReference.CLAMP_TO_GROUND,
        },
      });
      hotspotsEntitiesRef.current.push(entity);
    });
  }, [hotspots]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {!cesiumLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-mission-dark">
          <div className="text-mission-accent text-lg font-mono">Loading Cesium...</div>
        </div>
      )}
    </div>
  );
}

function computeOrbitPath(lat: number, lon: number, altKm: number): import("cesium").Cartesian3[] {
  if (typeof window === "undefined") return [];
  const Cesium = (window as any).Cesium;
  if (!Cesium) return [];

  const points: import("cesium").Cartesian3[] = [];
  const period = 90 * 60;
  const steps = 120;
  const stepSize = period / steps;

  for (let i = 0; i < steps; i++) {
    const t = (i / steps) * period;
    const angle = (t / period) * 360;
    const latRad = (lat * Math.PI) / 180;
    const lonRad = (lon * Math.PI) / 180;
    const orbitLat = Math.asin(Math.sin(latRad) * Math.cos((angle * Math.PI) / 180) + Math.cos(latRad) * Math.sin((angle * Math.PI) / 180) * 0);
    const orbitLon = lonRad + Math.atan2(Math.sin((angle * Math.PI) / 180) * Math.cos(latRad), Math.cos((angle * Math.PI) / 180));
    points.push(Cesium.Cartesian3.fromDegrees((orbitLon * 180) / Math.PI, (orbitLat * 180) / Math.PI, altKm * 1000));
  }
  return points;
}

function computeCameraFootprint(lat: number, lon: number, altKm: number): { positions: import("cesium").Cartesian3[] } | undefined {
  if (typeof window === "undefined") return undefined;
  const Cesium = (window as any).Cesium;
  if (!Cesium) return undefined;

  const fov = 15;
  const radius = altKm * Math.tan((fov * Math.PI) / 180);
  const distDeg = (radius / 111) * 2;
  const corners = [
    Cesium.Cartesian3.fromDegrees(lon - distDeg / 2, lat - distDeg / 2, 0),
    Cesium.Cartesian3.fromDegrees(lon + distDeg / 2, lat - distDeg / 2, 0),
    Cesium.Cartesian3.fromDegrees(lon + distDeg / 2, lat + distDeg / 2, 0),
    Cesium.Cartesian3.fromDegrees(lon - distDeg / 2, lat + distDeg / 2, 0),
  ];
  return { positions: corners };
}
