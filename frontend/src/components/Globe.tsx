"use client";
import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import type { DemoState } from "@/lib/demoEngine";

let Cesium: typeof import("cesium") | null = null;

const GROUND_STATIONS = [
  { name: "Boulder CO", lat: 40.015, lon: -105.2705, color: "#22c55e" },
  { name: "Fairbanks AK", lat: 64.8378, lon: -147.7164, color: "#3b82f6" },
  { name: "Svalbard", lat: 78.2232, lon: 15.6267, color: "#a855f7" },
  { name: "Singapore", lat: 1.3521, lon: 103.8198, color: "#f59e0b" },
  { name: "Punta Arenas", lat: -53.1638, lon: -70.9171, color: "#ef4444" },
];

const MAX_ORBITS_GROUND_TRACK = 2;
const ORBIT_PERIOD_S = 5400;
const CAMERA_THROTTLE_MS = 3000;

interface HotspotData {
  lat: number;
  lon: number;
  frp: number;
  confidence: string;
  id?: string;
}

interface GlobeProps {
  demoState?: DemoState | null;
}

function computeOrbitPath(
  lat: number,
  lon: number,
  altKm: number,
  C: typeof import("cesium")
): import("cesium").Cartesian3[] {
  const points: import("cesium").Cartesian3[] = [];
  const period = 90 * 60;
  const steps = 120;
  for (let i = 0; i < steps; i++) {
    const t = (i / steps) * period;
    const angle = (t / period) * 360;
    const latRad = (lat * Math.PI) / 180;
    const angleRad = (angle * Math.PI) / 180;
    const orbitLat = Math.asin(Math.sin(latRad) * Math.cos(angleRad));
    const orbitLon =
      (lon * Math.PI) / 180 +
      Math.atan2(
        Math.sin(angleRad) * Math.cos(latRad),
        Math.cos(angleRad)
      );
    points.push(
      C.Cartesian3.fromDegrees(
        (orbitLon * 180) / Math.PI,
        (orbitLat * 180) / Math.PI,
        altKm * 1000
      )
    );
  }
  return points;
}

function computeCameraFootprintHierarchy(
  lat: number,
  lon: number,
  altKm: number,
  C: typeof import("cesium")
): InstanceType<typeof import("cesium").PolygonHierarchy> | undefined {
  const fov = 15;
  const radius = altKm * Math.tan((fov * Math.PI) / 180);
  const distDeg = (radius / 111) * 2;
  return new C.PolygonHierarchy([
    C.Cartesian3.fromDegrees(lon - distDeg / 2, lat - distDeg / 2, 0),
    C.Cartesian3.fromDegrees(lon + distDeg / 2, lat - distDeg / 2, 0),
    C.Cartesian3.fromDegrees(lon + distDeg / 2, lat + distDeg / 2, 0),
    C.Cartesian3.fromDegrees(lon - distDeg / 2, lat + distDeg / 2, 0),
  ]);
}

export default function Globe({ demoState }: GlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const satelliteEntityRef = useRef<any>(null);
  const orbitPathRef = useRef<any>(null);
  const footprintRef = useRef<any>(null);
  const footprintConeRef = useRef<any>(null);
  const hotspotsEntitiesRef = useRef<any[]>([]);
  const groundStationEntitiesRef = useRef<any[]>([]);
  const visibilityCircleEntitiesRef = useRef<any[]>([]);
  const trackPointsRef = useRef<any[]>([]);
  const trackIndexRef = useRef(0);
  const initializedRef = useRef(false);
  const userInteractingRef = useRef(false);
  const lastUserInteractionRef = useRef(0);
  const lastCameraUpdateRef = useRef(0);
  const handlerRef = useRef<any>(null);
  const posRef = useRef<{ latitude: number; longitude: number; altitude_km: number } | null>(null);
  const [cesiumLoaded, setCesiumLoaded] = useState(false);
  const [selectedFirms, setSelectedFirms] = useState<HotspotData | null>(null);

  const pos = useMemo(
    () =>
      demoState
        ? {
            latitude: demoState.spacecraft.latitude,
            longitude: demoState.spacecraft.longitude,
            altitude_km: demoState.spacecraft.altitudeKm,
          }
        : null,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      demoState?.spacecraft.latitude,
      demoState?.spacecraft.longitude,
      demoState?.spacecraft.altitudeKm,
    ]
  );

  // Keep posRef current for Cesium callbacks (outside render is fine via effect)
  useEffect(() => {
    posRef.current = pos;
  }, [pos]);

  const trackUserInteraction = useCallback((viewer: any) => {
    const onInteract = () => {
      userInteractingRef.current = true;
      lastUserInteractionRef.current = Date.now();
    };
    const onStop = () => {
      setTimeout(() => {
        if (Date.now() - lastUserInteractionRef.current > 2000) {
          userInteractingRef.current = false;
        }
      }, 2000);
    };
    viewer.camera.changed.addEventListener(onInteract);
    viewer.camera.moveStart.addEventListener(onInteract);
    viewer.camera.moveEnd.addEventListener(onStop);
  }, []);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    let destroyed = false;

    const init = async () => {
      try {
        Cesium = await import("cesium");
        (window as any).Cesium = Cesium;

        const token = process.env.NEXT_PUBLIC_CESIUM_TOKEN || "";
        if (token) {
          Cesium.Ion.defaultAccessToken = token;
        }

        if (!containerRef.current || destroyed) return;

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

        // Use OpenStreetMap - no Ion token required
        viewer.imageryLayers.removeAll();
        viewer.imageryLayers.addImageryProvider(
          new Cesium.UrlTemplateImageryProvider({
            url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            subdomains: ["a", "b", "c"],
            maximumLevel: 18,
            credit: new Cesium.Credit("OpenStreetMap contributors", false),
          })
        );

        // Set dark globe background
        viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#0a0e17");
        viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0a0e17");

        trackUserInteraction(viewer);

        // Initial camera position
        viewer.camera.setView({
          destination: Cesium.Cartesian3.fromDegrees(0, 20, 25000000),
          orientation: { heading: 0, pitch: -Math.PI / 2, roll: 0 },
        });

        // Satellite entity
        const satelliteEntity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(0, 0, 500000),
          point: {
            pixelSize: 10,
            color: Cesium.Color.CYAN,
            outlineColor: Cesium.Color.WHITE,
            outlineWidth: 2,
          },
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

        // Ground track (past)
        viewer.entities.add({
          polyline: {
            positions: new Cesium.CallbackProperty(() => {
              const pts = trackPointsRef.current;
              const idx = trackIndexRef.current;
              return pts.slice(Math.max(0, idx - 200), idx + 1);
            }, false),
            width: 2.5,
            material: new Cesium.PolylineGlowMaterialProperty({
              glowPower: 0.15,
              color: Cesium.Color.fromCssColorString("#22c55e"),
            }),
          },
        });

        // Ground track (future)
        viewer.entities.add({
          polyline: {
            positions: new Cesium.CallbackProperty(() => {
              const pts = trackPointsRef.current;
              const idx = trackIndexRef.current;
              return pts.slice(idx, pts.length);
            }, false),
            width: 1.5,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.fromCssColorString("#64748b"),
              dashLength: 8,
            }),
          },
        });

        // Orbit path
        const orbitPath = viewer.entities.add({
          polyline: {
            positions: new Cesium.CallbackProperty(() => {
              const p = posRef.current;
              if (!Cesium || !p) return [];
              return computeOrbitPath(p.latitude, p.longitude, p.altitude_km, Cesium);
            }, false),
            width: 1.5,
            material: new Cesium.PolylineDashMaterialProperty({
              color: Cesium.Color.CYAN.withAlpha(0.3),
              dashLength: 16,
            }),
          },
        });

        // Camera footprint polygon - uses PolygonHierarchy
        const footprint = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(0, 0, 0),
          polygon: {
            hierarchy: new Cesium.CallbackProperty(() => {
              const p = posRef.current;
              if (!Cesium || !p) return undefined;
              return computeCameraFootprintHierarchy(
                p.latitude,
                p.longitude,
                p.altitude_km,
                Cesium
              );
            }, false),
            material: Cesium.Color.YELLOW.withAlpha(0.12),
            outline: true,
            outlineColor: Cesium.Color.YELLOW.withAlpha(0.4),
          },
        });

        // Camera footprint cone
        const footprintCone = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(0, 0, 0),
          cylinder: {
            length: new Cesium.CallbackProperty(() => {
              const p = posRef.current;
              if (!p) return 0;
              return p.altitude_km * 1000;
            }, false),
            topRadius: new Cesium.CallbackProperty(() => {
              const p = posRef.current;
              if (!p) return 0;
              const altM = p.altitude_km * 1000;
              return altM * Math.tan((15 * Math.PI) / 180);
            }, false),
            bottomRadius: 0,
            material: Cesium.Color.YELLOW.withAlpha(0.06),
            outline: true,
            outlineColor: Cesium.Color.YELLOW.withAlpha(0.2),
            numberOfVerticalLines: 0,
          },
        });

        // Ground stations
        GROUND_STATIONS.forEach((gs) => {
          const entity = viewer.entities.add({
            position: Cesium!.Cartesian3.fromDegrees(gs.lon, gs.lat, 0),
            point: {
              pixelSize: 7,
              color: Cesium!.Color.fromCssColorString(gs.color),
              outlineColor: Cesium!.Color.WHITE,
              outlineWidth: 1,
              heightReference: Cesium!.HeightReference.CLAMP_TO_GROUND,
            },
            label: {
              text: gs.name,
              font: "10px monospace",
              fillColor: Cesium!.Color.WHITE,
              style: Cesium!.LabelStyle.FILL_AND_OUTLINE,
              outlineWidth: 1,
              verticalOrigin: Cesium!.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium!.Cartesian2(0, -12),
              showBackground: true,
              backgroundColor: Cesium!.Color.fromCssColorString("#111827cc"),
              scale: 0.9,
            },
          });
          groundStationEntitiesRef.current.push(entity);

          const circlePositions: import("cesium").Cartesian3[] = [];
          const circleSteps = 64;
          const circleRadiusDeg = 5;
          for (let i = 0; i <= circleSteps; i++) {
            const angle = (i / circleSteps) * 2 * Math.PI;
            circlePositions.push(
              Cesium!.Cartesian3.fromDegrees(
                gs.lon + circleRadiusDeg * Math.cos(angle),
                gs.lat + circleRadiusDeg * Math.sin(angle),
                0
              )
            );
          }
          const circleEntity = viewer.entities.add({
            polyline: {
              positions: circlePositions,
              width: 1.5,
              material: Cesium!.Color.fromCssColorString(gs.color).withAlpha(0.35),
              clampToGround: true,
            },
          });
          visibilityCircleEntitiesRef.current.push(circleEntity);
        });

        satelliteEntityRef.current = satelliteEntity;
        orbitPathRef.current = orbitPath;
        footprintRef.current = footprint;
        footprintConeRef.current = footprintCone;
        viewerRef.current = viewer;

        if (!destroyed) {
          setCesiumLoaded(true);
        }
      } catch (err) {
        console.error("Cesium initialization failed:", err);
        if (!destroyed) {
          setCesiumLoaded(true);
        }
      }
    };

    init();

    return () => {
      destroyed = true;
      if (handlerRef.current) {
        handlerRef.current.destroy();
        handlerRef.current = null;
      }
      (viewerRef.current as any)?.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update satellite position, track points, throttled camera
  useEffect(() => {
    if (!viewerRef.current || !pos || !Cesium) return;

    const cartesianPos = Cesium.Cartesian3.fromDegrees(
      pos.longitude,
      pos.latitude,
      pos.altitude_km * 1000
    );

    if (satelliteEntityRef.current) {
      satelliteEntityRef.current.position = cartesianPos;
    }

    if (footprintConeRef.current) {
      footprintConeRef.current.position = cartesianPos;
    }

    trackPointsRef.current.push(cartesianPos);
    trackIndexRef.current = trackPointsRef.current.length - 1;
    const maxPoints = Math.ceil((MAX_ORBITS_GROUND_TRACK * ORBIT_PERIOD_S) / 5) * 3;
    while (trackPointsRef.current.length > maxPoints) {
      trackPointsRef.current.shift();
      trackIndexRef.current = Math.max(0, trackIndexRef.current - 1);
    }

    // Throttled camera follow
    const now = Date.now();
    if (
      !userInteractingRef.current &&
      now - lastCameraUpdateRef.current > CAMERA_THROTTLE_MS
    ) {
      lastCameraUpdateRef.current = now;
      viewerRef.current.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(
          pos.longitude,
          pos.latitude,
          pos.altitude_km * 1000 + 5000000
        ),
        orientation: { heading: 0, pitch: -Math.PI / 3, roll: 0 },
        duration: 1.0,
      });
    }
  }, [pos]);

  // Update hotspots with proper cleanup
  useEffect(() => {
    if (!viewerRef.current || !Cesium) return;
    const C = Cesium;
    const viewer = viewerRef.current;

    hotspotsEntitiesRef.current.forEach((e) => viewer.entities.remove(e));
    hotspotsEntitiesRef.current = [];

    if (handlerRef.current) {
      handlerRef.current.destroy();
      handlerRef.current = null;
    }

    const hotspots: HotspotData[] = Array.isArray(demoState?.hotspots)
      ? demoState!.hotspots
      : [];

    hotspots.forEach((h) => {
      const entity = viewer.entities.add({
        position: C.Cartesian3.fromDegrees(h.lon, h.lat, 0),
        point: {
          pixelSize: Math.min(4 + h.frp / 10, 12),
          color: h.frp > 50 ? C.Color.RED : C.Color.ORANGE,
          outlineColor: C.Color.YELLOW,
          outlineWidth: 1,
          heightReference: C.HeightReference.CLAMP_TO_GROUND,
        },
        label: {
          text: `FRP: ${h.frp.toFixed(0)} MW`,
          font: "9px monospace",
          fillColor: C.Color.WHITE,
          style: C.LabelStyle.FILL_AND_OUTLINE,
          outlineWidth: 1,
          verticalOrigin: C.VerticalOrigin.BOTTOM,
          pixelOffset: new C.Cartesian2(0, -10),
          showBackground: true,
          backgroundColor: C.Color.fromCssColorString("#7f1d1dcc"),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });
      (entity as any)._hotspotData = h;
      hotspotsEntitiesRef.current.push(entity);
    });

    const handler = new C.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click: any) => {
      const picked = viewer.scene.pick(click.position);
      if (C.defined(picked) && C.defined(picked.id) && (picked.id as any)._hotspotData) {
        const data = (picked.id as any)._hotspotData as HotspotData;
        setSelectedFirms(data);
        viewer.camera.flyTo({
          destination: C.Cartesian3.fromDegrees(data.lon, data.lat, 2000000),
          orientation: { heading: 0, pitch: -Math.PI / 3, roll: 0 },
          duration: 1.5,
        });
      }
    }, C.ScreenSpaceEventType.LEFT_CLICK);
    handlerRef.current = handler;

    return () => {
      if (handlerRef.current) {
        handlerRef.current.destroy();
        handlerRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demoState?.hotspots]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {!cesiumLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-mission-dark">
          <div className="text-mission-accent text-lg font-mono">Loading Cesium...</div>
        </div>
      )}
      {selectedFirms && (
        <div className="absolute top-3 right-3 bg-mission-panel border border-mission-border rounded-lg p-3 max-w-[220px] z-10">
          <div className="flex justify-between items-start mb-1">
            <span className="text-xs font-semibold text-red-400 uppercase">FIRMS Detection</span>
            <button onClick={() => setSelectedFirms(null)} className="text-slate-500 hover:text-slate-300 text-xs">&times;</button>
          </div>
          <div className="space-y-0.5 text-[10px] font-mono">
            <div className="flex justify-between"><span className="text-slate-400">Lat</span><span className="text-slate-200">{selectedFirms.lat.toFixed(4)}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Lon</span><span className="text-slate-200">{selectedFirms.lon.toFixed(4)}</span></div>
            <div className="flex justify-between"><span className="text-slate-400">FRP</span><span className="text-red-400 font-bold">{selectedFirms.frp.toFixed(1)} MW</span></div>
            <div className="flex justify-between"><span className="text-slate-400">Confidence</span><span className="text-slate-200">{selectedFirms.confidence}</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
