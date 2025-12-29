"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Interfaces for Airtable data
interface SlotData {
  slot: number;
  headline: string;
  storyId: string;
  pivotId: string;
}

interface SelectedSlotsData {
  id: string;
  issueId: string;
  issueDate: string;
  subjectLine: string;
  status: string;
  socialPostStatus: string;
  slots: SlotData[];
}

interface DecorationData {
  id: string;
  storyId: string;
  headline: string;
  imageStatus: string;
  slotOrder: number;
}

interface PrefilterData {
  id: string;
  storyId: string;
  headline: string;
  slot: number;
}

type StepStatus = "idle" | "running" | "completed" | "failed";

interface PipelineStep {
  id: number;
  name: string;
  description: string;
  schedule: string;
  status: StepStatus;
  lastRun?: string;
  storiesProcessed?: number;
}

const initialSteps: PipelineStep[] = [
  {
    id: 0,
    name: "Ingest",
    description: "Fetches articles from 19 RSS feeds and creates records in Airtable Newsletter Issue Stories",
    schedule: "8:00 PM EST",
    status: "idle",
    lastRun: undefined,
    storiesProcessed: undefined,
  },
  {
    id: 1,
    name: "Pre-Filter",
    description: "Filters candidate articles into 5 newsletter slots based on freshness, source credibility, and content relevance",
    schedule: "9:00 PM EST",
    status: "completed",
    lastRun: "2024-12-23 21:00:15",
    storiesProcessed: 47,
  },
  {
    id: 2,
    name: "Slot Selection",
    description: "5 sequential Claude agents select best story for each slot, enforcing diversity rules",
    schedule: "9:15 PM EST",
    status: "completed",
    lastRun: "2024-12-23 21:15:42",
    storiesProcessed: 5,
  },
  {
    id: 3,
    name: "Decoration",
    description: "Generates AI headlines, deks, bullet points, and image prompts for selected stories",
    schedule: "9:25 PM EST",
    status: "idle",
    lastRun: "2024-12-22 21:26:33",
    storiesProcessed: 5,
  },
  {
    id: 4,
    name: "Image Generation",
    description: "Creates images using Gemini/DALL-E and uploads to Cloudflare CDN",
    schedule: "9:30 PM EST",
    status: "idle",
    lastRun: "2024-12-22 21:31:18",
    storiesProcessed: 5,
  },
  {
    id: 5,
    name: "HTML Compile & Send",
    description: "Compiles final HTML email and sends via Mautic at 5 AM",
    schedule: "10:00 PM / 5:00 AM EST",
    status: "idle",
    lastRun: "2024-12-23 05:00:12",
  },
];

function getStatusColor(status: StepStatus): string {
  switch (status) {
    case "running":
      return "bg-blue-500";
    case "completed":
      return "bg-green-500";
    case "failed":
      return "bg-red-500";
    default:
      return "bg-zinc-600";
  }
}

function getStatusBadge(status: StepStatus) {
  switch (status) {
    case "running":
      return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Running</Badge>;
    case "completed":
      return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Completed</Badge>;
    case "failed":
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Failed</Badge>;
    default:
      return <Badge className="bg-zinc-500/20 text-zinc-400 border-zinc-500/30">Idle</Badge>;
  }
}

export default function PipelinePage() {
  const [steps, setSteps] = useState<PipelineStep[]>(initialSteps);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedSlots, setSelectedSlots] = useState<SelectedSlotsData | null>(null);
  const [decorations, setDecorations] = useState<DecorationData[]>([]);
  const [prefilterCount, setPrefilterCount] = useState(0);
  const [isCancelling, setIsCancelling] = useState(false);

  const [ingestStats, setIngestStats] = useState<{ totalArticles: number; todayCount: number } | null>(null);

  // Check if any step is running
  const hasRunningSteps = steps.some(step => step.status === "running");

  // Cancel all running jobs
  const cancelAllJobs = async () => {
    setIsCancelling(true);
    try {
      const response = await fetch("/api/jobs/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        // Reset all running steps to idle
        setSteps(prev =>
          prev.map(step =>
            step.status === "running" ? { ...step, status: "idle" as StepStatus } : step
          )
        );
        setIsRunningAll(false);
      } else {
        const data = await response.json();
        console.error("Failed to cancel jobs:", data.error);
      }
    } catch (error) {
      console.error("Error cancelling jobs:", error);
    } finally {
      setIsCancelling(false);
    }
  };

  const fetchPipelineData = useCallback(async () => {
    try {
      setLoading(true);

      // Fetch all data in parallel
      const [slotsRes, decorationsRes, prefilterRes, ingestRes] = await Promise.all([
        fetch("/api/slots"),
        fetch("/api/decorations"),
        fetch("/api/stories?type=prefilter"),
        fetch("/api/ingest"),
      ]);

      if (slotsRes.ok) {
        const slotsData = await slotsRes.json();
        setSelectedSlots(slotsData.selectedSlots);
      }

      if (decorationsRes.ok) {
        const decorationsData = await decorationsRes.json();
        setDecorations(decorationsData.decorations || []);
      }

      if (prefilterRes.ok) {
        const prefilterData = await prefilterRes.json();
        setPrefilterCount(prefilterData.stories?.length || 0);
      }

      if (ingestRes.ok) {
        const ingestData = await ingestRes.json();
        if (ingestData.success && ingestData.stats) {
          setIngestStats(ingestData.stats);
        }
      }
    } catch (error) {
      console.error("Error fetching pipeline data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPipelineData();
  }, [fetchPipelineData]);

  // Calculate stats from real data
  const slotsSelected = selectedSlots?.slots.filter(s => s.headline).length || 0;
  const imagesGenerated = decorations.filter(d => d.imageStatus === "generated").length;
  const newsletterStatus = selectedSlots?.status || "pending";

  const runStep = async (stepId: number) => {
    setSteps((prev) =>
      prev.map((step) =>
        step.id === stepId ? { ...step, status: "running" as StepStatus } : step
      )
    );

    try {
      // Map step IDs to their API endpoints
      const stepEndpoints: Record<number, string> = {
        0: "/api/ingest",      // Step 0: Ingestion
        1: "/api/prefilter",   // Step 1: Pre-Filter
        2: "/api/slots",       // Step 2: Slot Selection
        3: "/api/decorate",    // Step 3: Decoration
        4: "/api/compile",     // Step 4: HTML Compile
        5: "/api/send",        // Step 5: Send & Social
      };

      const endpoint = stepEndpoints[stepId];
      if (!endpoint) {
        throw new Error(`No endpoint configured for step ${stepId}`);
      }

      const response = await fetch(endpoint, { method: "POST" });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to trigger step");
      }

      setSteps((prev) =>
        prev.map((step) =>
          step.id === stepId
            ? {
                ...step,
                status: "completed" as StepStatus,
                lastRun: new Date().toISOString().replace("T", " ").slice(0, 19),
              }
            : step
        )
      );
    } catch (error) {
      console.error(`Failed to run step ${stepId}:`, error);
      setSteps((prev) =>
        prev.map((step) =>
          step.id === stepId ? { ...step, status: "error" as StepStatus } : step
        )
      );
    }
  };

  const runAllSteps = async () => {
    setIsRunningAll(true);
    for (const step of steps) {
      await new Promise<void>((resolve) => {
        runStep(step.id);
        setTimeout(resolve, 3500);
      });
    }
    setIsRunningAll(false);
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Newsletter Pipeline</h1>
          <p className="text-muted-foreground mt-1">
            Monitor and control the 5-step AI Editor workflow
          </p>
        </div>
        <div className="flex items-center gap-3">
          {(hasRunningSteps || isRunningAll) && (
            <Button
              onClick={cancelAllJobs}
              disabled={isCancelling}
              variant="destructive"
              className="bg-red-600 hover:bg-red-700"
            >
              {isCancelling ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Stopping...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z" />
                  </svg>
                  Stop All Jobs
                </>
              )}
            </Button>
          )}
          <Button
            onClick={runAllSteps}
            disabled={isRunningAll}
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
          >
            {isRunningAll ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Running Pipeline...
              </>
            ) : (
              "Run Full Pipeline"
            )}
          </Button>
        </div>
      </div>

      {/* Today's Issue Preview - TOP */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Today's Issue Preview</CardTitle>
          <CardDescription>
            {selectedSlots?.issueDate || "Loading..."}
            {selectedSlots?.subjectLine && (
              <span className="ml-2 text-primary">— {selectedSlots.subjectLine}</span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-muted-foreground text-center py-8">Loading issue data...</div>
          ) : selectedSlots ? (
            <div className="grid grid-cols-5 gap-4">
              {selectedSlots.slots.map((slotData) => {
                // Find decoration for this slot - match by storyId or slot order
                const decoration = decorations.find(d =>
                  d.storyId === slotData.storyId || d.slotOrder === slotData.slot
                );
                const slotLabels: Record<number, string> = {
                  1: "Jobs/Economy",
                  2: "Tier 1 AI",
                  3: "Industry",
                  4: "Emerging",
                  5: "Consumer",
                };
                return (
                  <div
                    key={slotData.slot}
                    className="p-4 rounded-lg bg-muted border border-border"
                  >
                    <div className="text-xs text-primary font-medium mb-2">
                      Slot {slotData.slot}: {slotLabels[slotData.slot]}
                    </div>
                    <div className="text-sm text-foreground font-medium line-clamp-2 mb-2">
                      {slotData.headline || "Not selected"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {!slotData.headline ? (
                        "Pending selection"
                      ) : decoration?.imageStatus === "generated" ? (
                        <span className="text-green-500">✓ Ready to send</span>
                      ) : (
                        <span className="text-yellow-500">Image pending</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-muted-foreground text-center py-8">No issue data available</div>
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-5 gap-4 mb-8">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-foreground">
              {loading ? "..." : ingestStats?.totalArticles || 0}
            </div>
            <div className="text-sm text-muted-foreground">Articles Ingested</div>
            {ingestStats?.todayCount !== undefined && ingestStats.todayCount > 0 && (
              <div className="text-xs text-primary mt-1">+{ingestStats.todayCount} today</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-foreground">
              {loading ? "..." : prefilterCount}
            </div>
            <div className="text-sm text-muted-foreground">Stories Pre-Filtered</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-foreground">
              {loading ? "..." : slotsSelected}
            </div>
            <div className="text-sm text-muted-foreground">Slots Selected</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-foreground">
              {loading ? "..." : imagesGenerated}
            </div>
            <div className="text-sm text-muted-foreground">Images Generated</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className={`text-2xl font-bold ${
              newsletterStatus === "sent" ? "text-green-500" :
              newsletterStatus === "pending" ? "text-yellow-500" : "text-muted-foreground"
            }`}>
              {loading ? "..." : newsletterStatus.charAt(0).toUpperCase() + newsletterStatus.slice(1)}
            </div>
            <div className="text-sm text-muted-foreground">Newsletter Status</div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Steps */}
      <div className="space-y-4">
        {steps.map((step, index) => (
          <Card key={step.id}>
            <CardContent className="p-6">
              <div className="flex items-start gap-6">
                {/* Step Number */}
                <div className="flex-shrink-0">
                  <div
                    className={`h-12 w-12 rounded-full flex items-center justify-center text-lg font-bold text-white ${getStatusColor(step.status)}`}
                  >
                    {step.id}
                  </div>
                  {index < steps.length - 1 && (
                    <div className="w-0.5 h-8 bg-border mx-auto mt-2" />
                  )}
                </div>

                {/* Step Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-foreground">
                      Step {step.id}: {step.name}
                    </h3>
                    {getStatusBadge(step.status)}
                  </div>
                  <p className="text-muted-foreground text-sm mb-3">{step.description}</p>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Scheduled: {step.schedule}</span>
                    </div>
                    {step.lastRun && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Last run: {step.lastRun}</span>
                      </div>
                    )}
                    {step.storiesProcessed !== undefined && (
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        <span>{step.storiesProcessed} stories</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex-shrink-0 flex items-center gap-2">
                  {step.status === "running" ? (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled
                      >
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Running...
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={cancelAllJobs}
                        disabled={isCancelling}
                        className="bg-red-600 hover:bg-red-700"
                      >
                        {isCancelling ? "Stopping..." : "Stop"}
                      </Button>
                    </>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => runStep(step.id)}
                    >
                      Run Step
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

    </div>
  );
}
