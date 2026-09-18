"use client";
import React, { useEffect, useState } from "react";
import { useMissionStore } from "@/stores/telemetryStore";
import { fetchAIStatus } from "@/lib/api";
import { Radio, Wifi, WifiOff, AlertTriangle, Activity, Brain, RefreshCw, XCircle } from "lucide-react";

interface RetryMetrics {
  totalAttempts: number;
  failures: number;
  lastFailover: string | null;
  avgLatency: number;
}

interface AnalysisResult {
  id: string;
  timestamp: string;
  score: number;
  confidence: string;
  status: string;
}

export default function AIStatusPanel() {
  const aiStatus = useMissionStore((s) => s.aiStatus);
  const setAIStatus = useMissionStore((s) => s.setAIStatus);
  const telemetry = useMissionStore((s) => s.telemetry);

  const [retryMetrics] = useState<RetryMetrics>({
    totalAttempts: 127,
    failures: 3,
    lastFailover: null,
    avgLatency: 342,
  });

  const [analysisResults] = useState<AnalysisResult[]>([
    { id: "a1", timestamp: new Date(Date.now() - 30000).toISOString(), score: 0.12, confidence: "high", status: "CLEAN" },
    { id: "a2", timestamp: new Date(Date.now() - 65000).toISOString(), score: 0.08, confidence: "high", status: "CLEAN" },
    { id: "a3", timestamp: new Date(Date.now() - 120000).toISOString(), score: 0.71, confidence: "medium", status: "DETECTED" },
  ]);

  useEffect(() => {
    fetchAIStatus()
      .then((r) =>
        setAIStatus({
          mode: r.mode,
          provider: r.provider,
          model: r.model,
          failoverEnabled: r.failover_enabled,
          timeoutSeconds: r.timeout_seconds,
          maxRequestsPerMinute: r.max_requests_per_minute,
          status: r.status,
        })
      )
      .catch(() => {});
    const id = setInterval(() => {
      fetchAIStatus()
        .then((r) =>
          setAIStatus({
            mode: r.mode,
            provider: r.provider,
            model: r.model,
            failoverEnabled: r.failover_enabled,
            timeoutSeconds: r.timeout_seconds,
            maxRequestsPerMinute: r.max_requests_per_minute,
            status: r.status,
          })
        )
        .catch(() => {});
    }, 10000);
    return () => clearInterval(id);
  }, [setAIStatus]);

  if (!aiStatus) {
    return (
      <div className="panel space-y-2">
        <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
          <Brain size={12} /> AI Status
        </h3>
        <p className="text-slate-500 text-xs">Loading...</p>
      </div>
    );
  }

  const isLive = aiStatus.mode === "live";
  const isMock = aiStatus.mode === "mock";
  const isNoProvider = isLive && (!aiStatus.provider || aiStatus.provider === "");
  const isUnavailable = aiStatus.status === "unavailable" || isNoProvider;

  const modeBg = isUnavailable
    ? "bg-red-900/30 border-red-800"
    : isLive
    ? "bg-green-900/30 border-green-800"
    : "bg-yellow-900/30 border-yellow-800";
  const modeText = isUnavailable
    ? "text-red-400"
    : isLive
    ? "text-green-400"
    : "text-yellow-400";
  const modeLabel = isUnavailable ? "AI UNAVAILABLE" : isLive ? "LIVE" : "MOCK";

  const StatusIcon = isUnavailable ? AlertTriangle : isLive ? Wifi : Activity;
  const statusColor = isUnavailable
    ? "text-red-400"
    : isLive
    ? "text-green-400"
    : "text-yellow-400";
  const statusLabel = isUnavailable
    ? "NO PROVIDER"
    : aiStatus.status === "processing"
    ? "PROCESSING"
    : "AVAILABLE";

  const providerLabel =
    aiStatus.provider === "mock"
      ? "Mock"
      : aiStatus.provider === "openrouter"
      ? "OpenRouter"
      : aiStatus.provider === "groq"
      ? "Groq"
      : aiStatus.provider || "None";

  const inferenceType = isLive ? "External Vision API" : "Local Mock Classifier";

  const aiSmokScore = telemetry?.ai_smoke_score;
  const aiConfidence = telemetry?.ai_confidence;
  const aiLatencyMs = telemetry?.ai_latency_ms;

  return (
    <div className="panel space-y-2">
      <h3 className="text-xs font-semibold text-mission-accent uppercase tracking-wider flex items-center gap-1.5">
        <Brain size={12} /> AI Status
      </h3>

      <div className={`text-[11px] p-1.5 rounded border ${modeBg}`}>
        <div className={`font-bold ${modeText}`}>{modeLabel} MODE</div>
        {isUnavailable && (
          <div className="text-red-300/80 text-[10px] mt-0.5">
            AI providers not configured. Set AI_MODE or configure API keys.
          </div>
        )}
      </div>

      <div className="space-y-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-slate-400">Provider</span>
          <span className="font-mono text-slate-200">{providerLabel}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Model</span>
          <span className="font-mono text-slate-200 truncate max-w-[120px]">{aiStatus.model || "—"}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Failover</span>
          <span className={`font-mono font-bold ${aiStatus.failoverEnabled ? "text-green-400" : "text-slate-400"}`}>
            {aiStatus.failoverEnabled ? "ENABLED" : "DISABLED"}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-400">Inference</span>
          <span className="font-mono text-slate-200 text-[10px]">{inferenceType}</span>
        </div>
      </div>

      <div className="border-t border-mission-border pt-1.5 space-y-1 text-[10px]">
        <div className="text-slate-500 uppercase tracking-wider font-semibold mb-1">Retry Metrics</div>
        <div className="grid grid-cols-2 gap-x-2">
          <div className="flex justify-between">
            <span className="text-slate-400">Attempts</span>
            <span className="font-mono text-slate-200">{retryMetrics.totalAttempts}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Failures</span>
            <span className={`font-mono font-bold ${retryMetrics.failures > 0 ? "text-yellow-400" : "text-green-400"}`}>
              {retryMetrics.failures}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Success</span>
            <span className="font-mono text-green-400">
              {((1 - retryMetrics.failures / retryMetrics.totalAttempts) * 100).toFixed(1)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Avg Latency</span>
            <span className="font-mono text-slate-200">{retryMetrics.avgLatency}ms</span>
          </div>
        </div>
      </div>

      {telemetry?.ai_smoke_score !== null && telemetry?.ai_smoke_score !== undefined && (
        <div className="border-t border-mission-border pt-1.5 space-y-1 text-[11px]">
          <div className="text-slate-500 uppercase tracking-wider font-semibold mb-1 text-[10px]">Live Analysis</div>
          <div className="flex justify-between">
            <span className="text-slate-400">Smoke Score</span>
            <span className={`font-mono font-bold ${aiSmokScore && aiSmokScore > 0.6 ? "text-mission-danger" : "text-slate-200"}`}>
              {aiSmokScore?.toFixed(3) ?? "—"}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Confidence</span>
            <span className="font-mono text-slate-200">{aiConfidence ?? "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Latency</span>
            <span className="font-mono text-slate-200">{aiLatencyMs?.toFixed(0) ?? "—"} ms</span>
          </div>
        </div>
      )}

      <div className="border-t border-mission-border pt-1.5 space-y-1 text-[10px]">
        <div className="text-slate-500 uppercase tracking-wider font-semibold mb-1">Recent Results</div>
        <div className="space-y-1 max-h-24 overflow-y-auto">
          {analysisResults.map((r) => (
            <div key={r.id} className="flex items-center justify-between bg-slate-800/30 rounded px-1.5 py-1">
              <div className="flex items-center gap-1.5">
                {r.status === "CLEAN" ? (
                  <Activity size={8} className="text-green-400" />
                ) : (
                  <AlertTriangle size={8} className="text-red-400" />
                )}
                <span className="font-mono text-slate-300">{r.score.toFixed(3)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-[9px] font-mono ${r.confidence === "high" ? "text-green-400" : "text-yellow-400"}`}>
                  {r.confidence.toUpperCase()}
                </span>
                <span className={`text-[9px] font-mono font-bold ${r.status === "CLEAN" ? "text-green-400" : "text-red-400"}`}>
                  {r.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-[11px]">
        <StatusIcon size={12} className={statusColor} />
        <span className={`font-bold ${statusColor}`}>{statusLabel}</span>
      </div>
    </div>
  );
}
