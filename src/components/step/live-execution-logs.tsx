"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Radio, AlertCircle, WifiOff } from "lucide-react";

type TimeFilter = "live" | "1h" | "12h" | "24h";

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  message: string;
  type: string;
  service: string;
}

interface LiveExecutionLogsProps {
  stepId: number;
  title?: string;
}

// Filter labels for the buttons
const FILTER_LABELS: Record<TimeFilter, string> = {
  live: "Live",
  "1h": "Past Hour",
  "12h": "Past 12h",
  "24h": "Past 24h",
};

// Parse log level from message if not provided
function inferLogLevel(message: string, level: string): string {
  if (level && level !== "info") return level;

  const lowerMsg = message.toLowerCase();
  if (lowerMsg.includes("error") || lowerMsg.includes("failed") || lowerMsg.includes("!!!")) {
    return "error";
  }
  if (lowerMsg.includes("warning") || lowerMsg.includes("warn")) {
    return "warn";
  }
  if (lowerMsg.includes("debug")) {
    return "debug";
  }
  return level || "info";
}

// Format timestamp for display (ET timezone)
function formatLogTime(timestamp: string): string {
  const d = new Date(timestamp);
  return d.toLocaleTimeString("en-US", {
    timeZone: "America/New_York",
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

// Extract slot number from log message if present
function extractSlotNumber(message: string): number | null {
  const match = message.match(/[Ss]lot\s*(\d)/);
  return match ? parseInt(match[1], 10) : null;
}

export function LiveExecutionLogs({ stepId, title = "Execution Logs" }: LiveExecutionLogsProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<TimeFilter>("live");
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setConnectionError(null);
    setIsConnected(false);

    // Open SSE connection
    const stepParam = stepId === 0 ? "0" : stepId === 1 ? "1" : "all";
    const url = `/api/logs/stream?stepId=${stepParam}&filter=${filter}`;

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setConnectionError(null);
    };

    eventSource.onerror = (e) => {
      console.error("[LiveLogs] SSE error:", e);
      setIsConnected(false);
      // Don't set error immediately - SSE can recover
      setTimeout(() => {
        if (eventSourceRef.current?.readyState === EventSource.CLOSED) {
          setConnectionError("Connection lost. Refresh to reconnect.");
        }
      }, 5000);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Check for error in response
        if (data.error) {
          setConnectionError(data.error);
          return;
        }

        // Handle array of logs
        const newLogs: LogEntry[] = Array.isArray(data) ? data : (data.logs || []);

        if (newLogs.length > 0) {
          setLogs((prev) => {
            if (filter === "live") {
              // Append new logs, keep last 500
              const combined = [...prev, ...newLogs];
              return combined.slice(-500);
            }
            // Replace for historical views
            return newLogs;
          });
        }
      } catch (e) {
        console.error("[LiveLogs] Parse error:", e);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [stepId, filter]);

  // Auto-scroll for live view
  useEffect(() => {
    if (filter === "live" && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, filter]);

  // Handle filter change
  const handleFilterChange = (newFilter: TimeFilter) => {
    setLogs([]); // Clear logs when changing filter
    setFilter(newFilter);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            {title}
            {filter === "live" && (
              <Badge
                variant={isConnected ? "default" : "destructive"}
                className={cn(
                  "text-xs",
                  isConnected && "bg-green-100 text-green-800"
                )}
              >
                {isConnected ? (
                  <>
                    <Radio className="h-3 w-3 mr-1 animate-pulse" />
                    Live
                  </>
                ) : (
                  <>
                    <WifiOff className="h-3 w-3 mr-1" />
                    Disconnected
                  </>
                )}
              </Badge>
            )}
          </CardTitle>

          {/* Time Filter Buttons - Render Style */}
          <div className="flex gap-1">
            {(Object.keys(FILTER_LABELS) as TimeFilter[]).map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "ghost"}
                size="sm"
                onClick={() => handleFilterChange(f)}
                className={cn(
                  "text-xs h-7 px-2",
                  filter === f && "bg-zinc-900 text-white hover:bg-zinc-800"
                )}
              >
                {FILTER_LABELS[f]}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Connection Error Banner */}
        {connectionError && (
          <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded-md flex items-center gap-2 text-sm text-amber-800">
            <AlertCircle className="h-4 w-4" />
            {connectionError}
          </div>
        )}

        {/* Log Display */}
        <div className="h-[400px] overflow-y-auto bg-zinc-950 rounded-md p-3 font-mono text-sm">
          {logs.length === 0 ? (
            <div className="text-zinc-500 text-center py-8">
              {connectionError ? (
                <p>Unable to connect to log stream</p>
              ) : filter === "live" ? (
                <>
                  <Radio className="h-6 w-6 mx-auto mb-2 animate-pulse" />
                  <p>Waiting for logs...</p>
                  <p className="text-xs mt-1">Logs will appear when jobs run</p>
                </>
              ) : (
                <p>No logs found in this time period</p>
              )}
            </div>
          ) : (
            logs.map((log) => {
              const level = inferLogLevel(log.message, log.level);
              const slotNum = extractSlotNumber(log.message);

              return (
                <div
                  key={log.id}
                  className={cn(
                    "py-0.5 flex gap-2 hover:bg-zinc-900/50",
                    level === "error" && "text-red-400",
                    level === "warn" && "text-amber-400",
                    level === "info" && "text-zinc-300",
                    level === "debug" && "text-zinc-500"
                  )}
                >
                  {/* Timestamp */}
                  <span className="text-zinc-500 shrink-0 w-20">
                    {formatLogTime(log.timestamp)}
                  </span>

                  {/* Level badge */}
                  <span
                    className={cn(
                      "shrink-0 w-14 uppercase text-xs",
                      level === "error" && "text-red-500",
                      level === "warn" && "text-amber-500",
                      level === "info" && "text-zinc-400",
                      level === "debug" && "text-zinc-600"
                    )}
                  >
                    [{level}]
                  </span>

                  {/* Slot badge (if present) */}
                  {slotNum && (
                    <Badge
                      variant="outline"
                      className="shrink-0 text-xs h-5 px-1 border-zinc-700 text-zinc-400"
                    >
                      Slot {slotNum}
                    </Badge>
                  )}

                  {/* Message */}
                  <span className="break-all">{log.message}</span>
                </div>
              );
            })
          )}
          <div ref={logsEndRef} />
        </div>

        {/* Footer with log count */}
        <div className="mt-2 flex items-center justify-between text-xs text-zinc-500">
          <span>
            {logs.length} log{logs.length !== 1 ? "s" : ""} displayed
          </span>
          {filter === "live" && (
            <span>Auto-updating every 3 seconds</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
