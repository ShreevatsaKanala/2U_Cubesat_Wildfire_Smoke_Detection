"use client";
import { useEffect, useRef, useCallback } from "react";
import { useMissionStore, SpacecraftTelemetry } from "@/stores/telemetryStore";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useTelemetrySocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const { setTelemetry, setConnected, connected } = useMissionStore();

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/ws/telemetry`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "telemetry") {
          setTelemetry(data.payload as SpacecraftTelemetry);
        }
      } catch {}
    };
  }, [setTelemetry, setConnected]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);
}
