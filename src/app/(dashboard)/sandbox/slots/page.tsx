"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

function MaterialIcon({ name, className }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className ?? ""}`}>
      {name}
    </span>
  );
}

// Slot definitions with descriptions
const SLOTS = [
  {
    num: 1,
    name: "Slot 1: Breaking News",
    icon: "bolt",
    description: "Hot off the press (0-2 hours old)",
    color: "red",
  },
  {
    num: 2,
    name: "Slot 2: AI Research",
    icon: "science",
    description: "Research & developments (0-12 hours old)",
    color: "purple",
  },
  {
    num: 3,
    name: "Slot 3: Startups & Products",
    icon: "rocket_launch",
    description: "Product launches & funding (0-24 hours old)",
    color: "blue",
  },
  {
    num: 4,
    name: "Slot 4: Industry Analysis",
    icon: "analytics",
    description: "Deeper takes & opinions (0-36 hours old)",
    color: "emerald",
  },
  {
    num: 5,
    name: "Slot 5: Feature Story",
    icon: "auto_stories",
    description: "Longer reads & evergreen (0-48 hours old)",
    color: "amber",
  },
];

const COLOR_CLASSES: Record<string, { bg: string; text: string; border: string; light: string }> = {
  red: { bg: "bg-red-100", text: "text-red-600", border: "border-red-200", light: "bg-red-50/30" },
  purple: { bg: "bg-purple-100", text: "text-purple-600", border: "border-purple-200", light: "bg-purple-50/30" },
  blue: { bg: "bg-blue-100", text: "text-blue-600", border: "border-blue-200", light: "bg-blue-50/30" },
  emerald: { bg: "bg-emerald-100", text: "text-emerald-600", border: "border-emerald-200", light: "bg-emerald-50/30" },
  amber: { bg: "bg-amber-100", text: "text-amber-600", border: "border-amber-200", light: "bg-amber-50/30" },
};

interface SlotState {
  isRunning: boolean;
  jobId: string | null;
  jobStatus: "queued" | "started" | "finished" | "failed" | null;
  elapsedTime: number;
  result: { written: number; elapsed: number } | null;
}

export default function SlotTestingPage() {
  // State for all 5 slots
  const [slotStates, setSlotStates] = useState<Record<number, SlotState>>({
    1: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    2: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    3: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    4: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    5: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
  });

  const [isCancelling, setIsCancelling] = useState<number | null>(null);

  // Update a specific slot's state
  const updateSlotState = (slotNum: number, updates: Partial<SlotState>) => {
    setSlotStates(prev => ({
      ...prev,
      [slotNum]: { ...prev[slotNum], ...updates },
    }));
  };

  // Check if any slot is running
  const anySlotRunning = Object.values(slotStates).some(s => s.isRunning);

  // Cancel a running job
  const cancelJob = async (slotNum: number) => {
    const jobId = slotStates[slotNum].jobId;
    if (!jobId) return;

    setIsCancelling(slotNum);
    try {
      const response = await fetch("/api/jobs/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId }),
      });

      const data = await response.json();
      if (response.ok) {
        toast.success(`Slot ${slotNum} job cancelled`);
        updateSlotState(slotNum, {
          isRunning: false,
          jobId: null,
          jobStatus: null,
        });
      } else {
        toast.error(data.error || "Failed to cancel job");
      }
    } catch (error) {
      console.error("Error cancelling job:", error);
      toast.error("Failed to cancel job");
    } finally {
      setIsCancelling(null);
    }
  };

  // Run a single slot
  const runSlot = async (slotNum: number) => {
    const jobName = `prefilter_slot_${slotNum}`;

    updateSlotState(slotNum, {
      isRunning: true,
      elapsedTime: 0,
      result: null,
    });

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: jobName }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        updateSlotState(slotNum, {
          jobId: data.job_id,
          jobStatus: "queued",
        });
        toast.success(`Slot ${slotNum} Started`, {
          description: `Prefilter job queued successfully`,
        });
      } else {
        updateSlotState(slotNum, { isRunning: false });
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      updateSlotState(slotNum, { isRunning: false });
      toast.error("Error", {
        description: error instanceof Error ? error.message : "Failed to start job",
      });
    }
  };

  // Poll job status for each running slot
  useEffect(() => {
    const intervals: Record<number, { poll: NodeJS.Timeout; timer: NodeJS.Timeout }> = {};

    SLOTS.forEach(slot => {
      const state = slotStates[slot.num];
      if (!state.jobId) return;

      const startTime = Date.now();

      // Timer for elapsed time
      intervals[slot.num] = {
        timer: setInterval(() => {
          updateSlotState(slot.num, {
            elapsedTime: Math.floor((Date.now() - startTime) / 1000),
          });
        }, 1000),
        poll: setInterval(async () => {
          try {
            const response = await fetch(`/api/jobs/${state.jobId}`);
            const status = await response.json();

            if (status.status === "started" || status.status === "queued") {
              updateSlotState(slot.num, { jobStatus: status.status });
            }

            if (status.status === "finished" || status.status === "failed") {
              clearInterval(intervals[slot.num].poll);
              clearInterval(intervals[slot.num].timer);

              const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

              if (status.status === "finished") {
                const writtenCount = status.result?.written || 0;
                updateSlotState(slot.num, {
                  isRunning: false,
                  jobId: null,
                  jobStatus: "finished",
                  result: { written: writtenCount, elapsed: finalElapsed },
                });
                toast.success(`Slot ${slot.num} Completed`, {
                  description: `Wrote ${writtenCount} records to Airtable in ${finalElapsed}s`,
                });
              } else {
                updateSlotState(slot.num, {
                  isRunning: false,
                  jobId: null,
                  jobStatus: "failed",
                });
                toast.error(`Slot ${slot.num} Failed`, {
                  description: status.error || "Unknown error occurred",
                });
              }
            }
          } catch (error) {
            console.error(`Error polling slot ${slot.num} status:`, error);
          }
        }, 2000),
      };
    });

    return () => {
      Object.values(intervals).forEach(({ poll, timer }) => {
        clearInterval(poll);
        clearInterval(timer);
      });
    };
  }, [slotStates[1].jobId, slotStates[2].jobId, slotStates[3].jobId, slotStates[4].jobId, slotStates[5].jobId]);

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-100 text-indigo-600">
              <MaterialIcon name="grid_view" className="text-2xl" />
            </div>
            <div>
              <CardTitle className="text-xl">Slot Testing Dashboard</CardTitle>
              <CardDescription className="mt-1">
                Run individual prefilter slots to test Gemini API calls and Airtable writes
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Slot Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {SLOTS.map(slot => {
          const state = slotStates[slot.num];
          const colors = COLOR_CLASSES[slot.color];

          return (
            <Card
              key={slot.num}
              className={state.isRunning ? `${colors.border} ${colors.light}` : ""}
            >
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    state.isRunning ? "bg-blue-100 text-blue-600" : `${colors.bg} ${colors.text}`
                  }`}>
                    <MaterialIcon name={slot.icon} className="text-xl" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate">{slot.name}</CardTitle>
                    <CardDescription className="text-xs truncate">
                      {slot.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {state.isRunning ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200">
                        {state.jobStatus === "queued" ? "Queued..." : "Running..."}
                      </Badge>
                      <span className="font-mono text-lg font-bold text-blue-700">
                        {Math.floor(state.elapsedTime / 60)}:{String(state.elapsedTime % 60).padStart(2, "0")}
                      </span>
                    </div>
                    <Progress value={undefined} className="h-2 bg-blue-100" />
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-blue-600 truncate">
                        Job: {state.jobId?.slice(0, 8)}...
                      </span>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => cancelJob(slot.num)}
                        disabled={isCancelling === slot.num}
                        className="h-7 px-2 text-xs"
                      >
                        {isCancelling === slot.num ? "..." : "Stop"}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {state.result && (
                      <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-md px-3 py-2">
                        <MaterialIcon name="check_circle" className="text-base" />
                        <span>{state.result.written} records in {state.result.elapsed}s</span>
                      </div>
                    )}
                    {state.jobStatus === "failed" && (
                      <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
                        <MaterialIcon name="error" className="text-base" />
                        <span>Job failed</span>
                      </div>
                    )}
                    <Button
                      onClick={() => runSlot(slot.num)}
                      disabled={anySlotRunning}
                      className={`w-full gap-2 ${colors.bg} ${colors.text} hover:opacity-80`}
                      variant="secondary"
                    >
                      <MaterialIcon name="play_arrow" className="text-lg" />
                      Run Slot {slot.num}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Info Card */}
      <Card className="border-indigo-200 bg-indigo-50/50">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <MaterialIcon name="info" className="text-xl text-indigo-600 mt-0.5" />
            <div className="text-sm text-indigo-800">
              <p className="font-medium mb-1">How Slot Testing Works:</p>
              <ul className="list-disc list-inside space-y-1 text-indigo-700">
                <li>Each slot runs independently with its own Gemini prompt</li>
                <li>Results are written to Airtable immediately after each slot completes</li>
                <li>Slots have different freshness windows (Slot 1 = newest, Slot 5 = oldest)</li>
                <li>Only one slot can run at a time to avoid API rate limits</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
