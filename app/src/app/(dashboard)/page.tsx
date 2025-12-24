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
    id: 1,
    name: "Pre-Filter",
    description: "Filters candidate articles into 5 newsletter slots based on freshness, source credibility, and content relevance",
    schedule: "9:00 PM EST",
    status: "idle",
  },
  {
    id: 2,
    name: "Slot Selection",
    description: "5 sequential Claude agents select best story for each slot, enforcing diversity rules",
    schedule: "11:55 PM EST",
    status: "idle",
  },
  {
    id: 3,
    name: "Decoration",
    description: "Generates AI headlines, deks, bullet points, and image prompts for selected stories",
    schedule: "9:25 PM EST",
    status: "idle",
  },
  {
    id: 4,
    name: "Image Generation",
    description: "Creates images using AI and uploads to Cloudflare CDN",
    schedule: "9:30 PM EST",
    status: "idle",
  },
  {
    id: 5,
    name: "HTML Compile & Send",
    description: "Compiles final HTML email and sends via Mautic at 5 AM",
    schedule: "10:00 PM / 5:00 AM EST",
    status: "idle",
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
      return "bg-gray-400";
  }
}

function getStatusBadge(status: StepStatus) {
  switch (status) {
    case "running":
      return <Badge className="bg-blue-100 text-blue-700 border-blue-200">Running</Badge>;
    case "completed":
      return <Badge className="bg-green-100 text-green-700 border-green-200">Completed</Badge>;
    case "failed":
      return <Badge className="bg-red-100 text-red-700 border-red-200">Failed</Badge>;
    default:
      return <Badge className="bg-gray-100 text-gray-600 border-gray-200">Ready</Badge>;
  }
}

export default function PipelinePage() {
  const [steps, setSteps] = useState<PipelineStep[]>(initialSteps);
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedSlots, setSelectedSlots] = useState<SelectedSlotsData | null>(null);
  const [decorations, setDecorations] = useState<DecorationData[]>([]);
  const [prefilterCount, setPrefilterCount] = useState(0);

  const fetchPipelineData = useCallback(async () => {
    try {
      setLoading(true);

      // Fetch all data in parallel
      const [slotsRes, decorationsRes, prefilterRes] = await Promise.all([
        fetch("/api/slots"),
        fetch("/api/decorations"),
        fetch("/api/stories?type=prefilter"),
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

    // Simulate API call
    setTimeout(() => {
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
    }, 3000);
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
          <h1 className="text-2xl font-bold text-gray-900">Newsletter Pipeline</h1>
          <p className="text-gray-500 mt-1">
            Monitor and control the 5-step AI Editor workflow
          </p>
        </div>
        <Button
          onClick={runAllSteps}
          disabled={isRunningAll}
          className="bg-orange-500 hover:bg-orange-600 text-white"
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

      {/* Quick Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-gray-900">
              {loading ? "..." : prefilterCount}
            </div>
            <div className="text-sm text-gray-500">Stories Pre-Filtered</div>
          </CardContent>
        </Card>
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-gray-900">
              {loading ? "..." : slotsSelected}
            </div>
            <div className="text-sm text-gray-500">Slots Selected</div>
          </CardContent>
        </Card>
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-gray-900">
              {loading ? "..." : imagesGenerated}
            </div>
            <div className="text-sm text-gray-500">Images Generated</div>
          </CardContent>
        </Card>
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardContent className="p-4">
            <div className={`text-2xl font-bold ${
              newsletterStatus === "sent" ? "text-green-600" :
              newsletterStatus === "pending" ? "text-amber-600" : "text-gray-500"
            }`}>
              {loading ? "..." : newsletterStatus.charAt(0).toUpperCase() + newsletterStatus.slice(1)}
            </div>
            <div className="text-sm text-gray-500">Newsletter Status</div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline Steps */}
      <div className="space-y-4">
        {steps.map((step, index) => (
          <Card key={step.id} className="bg-white border-gray-200 shadow-sm">
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
                    <div className="w-0.5 h-8 bg-gray-200 mx-auto mt-2" />
                  )}
                </div>

                {/* Step Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Step {step.id}: {step.name}
                    </h3>
                    {getStatusBadge(step.status)}
                  </div>
                  <p className="text-gray-500 text-sm mb-3">{step.description}</p>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2 text-gray-500">
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Scheduled: {step.schedule}</span>
                    </div>
                    {step.lastRun && (
                      <div className="flex items-center gap-2 text-gray-500">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>Last run: {step.lastRun}</span>
                      </div>
                    )}
                    {step.storiesProcessed !== undefined && (
                      <div className="flex items-center gap-2 text-gray-500">
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                        <span>{step.storiesProcessed} stories</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex-shrink-0">
                  <Button
                    size="sm"
                    onClick={() => runStep(step.id)}
                    disabled={step.status === "running"}
                    className="bg-orange-500 hover:bg-orange-600 text-white"
                  >
                    {step.status === "running" ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Running...
                      </>
                    ) : (
                      "Run Step"
                    )}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Today's Issue Preview */}
      <Card className="bg-white border-gray-200 shadow-sm mt-8">
        <CardHeader>
          <CardTitle className="text-gray-900">Today's Issue Preview</CardTitle>
          <CardDescription className="text-gray-500">
            {selectedSlots?.issueDate || "Loading..."}
            {selectedSlots?.subjectLine && (
              <span className="ml-2 text-orange-600">— {selectedSlots.subjectLine}</span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-gray-500 text-center py-8">Loading issue data...</div>
          ) : selectedSlots ? (
            <div className="grid grid-cols-5 gap-4">
              {selectedSlots.slots.map((slotData) => {
                // Find decoration for this slot to get image status
                const decoration = decorations.find(d => d.storyId === slotData.storyId);
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
                    className="p-4 rounded-lg bg-gray-50 border border-gray-200"
                  >
                    <div className="text-xs text-orange-600 font-medium mb-2">
                      Slot {slotData.slot}: {slotLabels[slotData.slot]}
                    </div>
                    <div className="text-sm text-gray-900 font-medium line-clamp-2 mb-2">
                      {slotData.headline || "Not selected"}
                    </div>
                    <div className="text-xs text-gray-500">
                      {!slotData.headline ? (
                        "Pending selection"
                      ) : decoration?.imageStatus === "generated" ? (
                        <span className="text-green-600">Ready to send</span>
                      ) : (
                        <span className="text-amber-600">Image pending</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">No issue data available</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
