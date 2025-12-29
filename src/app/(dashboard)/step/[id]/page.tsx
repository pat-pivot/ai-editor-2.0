"use client";

import { notFound } from "next/navigation";
import { use, useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { getStepConfig } from "@/lib/step-config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExecutionLogs } from "@/components/step/execution-logs";
import { SystemPrompts } from "@/components/step/system-prompts";
import { StepData } from "@/components/step/step-data";
import { Progress } from "@/components/ui/progress";

function MaterialIcon({ name, className }: { name: string; className?: string }) {
  return (
    <span className={`material-symbols-outlined ${className ?? ""}`}>
      {name}
    </span>
  );
}

interface PageProps {
  params: Promise<{ id: string }>;
}

// Map step ID to job name
const STEP_JOB_NAMES: Record<number, string> = {
  0: "ingest",
  1: "prefilter",
  2: "slot_selection",
  3: "decoration",
  4: "html_compile",
  5: "mautic_send",
};

// Step 0 has two jobs: ingest and ai_scoring
const STEP_0_JOBS = {
  ingest: { name: "Ingest Articles", icon: "download" },
  ai_scoring: { name: "Run AI Scoring", icon: "psychology" },
};

export default function StepPage({ params }: PageProps) {
  const { id } = use(params);
  const stepId = parseInt(id, 10);
  const [isRunning, setIsRunning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showCompletion, setShowCompletion] = useState(false);
  const [lastResult, setLastResult] = useState<{ processed: number; elapsed: number } | null>(null);
  const [activeTab, setActiveTab] = useState("logs");

  // Step 0 specific: Track AI Scoring job separately
  const [isAiScoringRunning, setIsAiScoringRunning] = useState(false);
  const [aiScoringJobId, setAiScoringJobId] = useState<string | null>(null);
  const [aiScoringJobStatus, setAiScoringJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [aiScoringElapsedTime, setAiScoringElapsedTime] = useState(0);
  const [currentJobType, setCurrentJobType] = useState<"ingest" | "ai_scoring" | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // Cancel running job
  const cancelJob = async () => {
    const currentJobId = currentJobType === "ai_scoring" ? aiScoringJobId : jobId;
    if (!currentJobId) return;

    setIsCancelling(true);
    try {
      const response = await fetch("/api/jobs/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId: currentJobId }),
      });

      const data = await response.json();
      if (response.ok) {
        toast.success("Job cancelled");
        // Reset state
        if (currentJobType === "ai_scoring") {
          setIsAiScoringRunning(false);
          setAiScoringJobId(null);
          setAiScoringJobStatus(null);
        } else {
          setIsRunning(false);
          setJobId(null);
          setJobStatus(null);
        }
        setCurrentJobType(null);
      } else {
        toast.error(data.error || "Failed to cancel job");
      }
    } catch (error) {
      console.error("Error cancelling job:", error);
      toast.error("Failed to cancel job");
    } finally {
      setIsCancelling(false);
    }
  };

  if (isNaN(stepId) || stepId < 0 || stepId > 5) {
    notFound();
  }

  const stepConfig = getStepConfig(stepId);

  if (!stepConfig) {
    notFound();
  }

  const handleRunNow = async (jobType?: "ingest" | "ai_scoring") => {
    // For Step 0, use the specified jobType; otherwise use the step's job name
    const jobName = stepId === 0 && jobType ? jobType : STEP_JOB_NAMES[stepId];
    if (!jobName) return;

    const jobDisplayName = stepId === 0 && jobType
      ? STEP_0_JOBS[jobType].name
      : stepConfig.name;

    // For Step 0 AI Scoring, use separate state
    if (stepId === 0 && jobType === "ai_scoring") {
      setIsAiScoringRunning(true);
      setAiScoringElapsedTime(0);
      setCurrentJobType("ai_scoring");
    } else {
      setIsRunning(true);
      setElapsedTime(0);
      setCurrentJobType(stepId === 0 ? "ingest" : null);
    }
    setShowCompletion(false);

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: jobName }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (stepId === 0 && jobType === "ai_scoring") {
          setAiScoringJobId(data.job_id);
          setAiScoringJobStatus("queued");
        } else {
          setJobId(data.job_id);
          setJobStatus("queued");
        }
        toast.success("Job Started", {
          description: `${jobDisplayName} job queued successfully`,
        });
      } else {
        if (stepId === 0 && jobType === "ai_scoring") {
          setIsAiScoringRunning(false);
        } else {
          setIsRunning(false);
        }
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      if (stepId === 0 && jobType === "ai_scoring") {
        setIsAiScoringRunning(false);
      } else {
        setIsRunning(false);
      }
      toast.error("Error", {
        description: error instanceof Error ? error.message : "Failed to start job",
      });
    }
  };

  // Poll job status until completion
  useEffect(() => {
    if (!jobId) return;

    const startTime = Date.now();

    // Update elapsed time every second
    const timerInterval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    // Poll job status every 2 seconds
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`);
        const status = await response.json();

        // Update job status for UI display
        if (status.status === "started" || status.status === "queued") {
          setJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsRunning(false);
          setJobId(null);
          setJobStatus(status.status);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const processedCount = status.result?.processed || status.result?.total_written || 0;
            setLastResult({ processed: processedCount, elapsed: finalElapsed });
            setShowCompletion(true);
            toast.success("Job Completed", {
              description: `Processed ${processedCount} stories in ${finalElapsed}s`,
            });
            // Trigger refresh in StepData component
            window.dispatchEvent(new CustomEvent("jobCompleted", { detail: { stepId } }));
          } else {
            toast.error("Job Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [jobId, stepId]);

  // Poll AI Scoring job status (Step 0 only)
  useEffect(() => {
    if (!aiScoringJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setAiScoringElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${aiScoringJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setAiScoringJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsAiScoringRunning(false);
          setAiScoringJobId(null);
          setAiScoringJobStatus(status.status);
          setCurrentJobType(null);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const processedCount = status.result?.articles_scored || status.result?.processed || 0;
            const storiesCreated = status.result?.newsletter_stories_created || 0;
            setLastResult({ processed: processedCount, elapsed: finalElapsed });
            setShowCompletion(true);
            toast.success("AI Scoring Completed", {
              description: `Scored ${processedCount} articles, created ${storiesCreated} Newsletter Stories in ${finalElapsed}s`,
            });
            window.dispatchEvent(new CustomEvent("jobCompleted", { detail: { stepId } }));
          } else {
            toast.error("AI Scoring Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling AI Scoring job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [aiScoringJobId, stepId]);

  // Mock execution data - in production this would come from an API
  const lastRun = {
    date: "Dec 23, 2025 9:00:15 PM",
    duration: "1m 42s",
    status: "success" as const,
  };

  const nextRun = "Dec 24, 2025 9:00:00 PM";

  return (
    <div className="p-6 space-y-6">
      {/* Step Header */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <MaterialIcon name={stepConfig.icon} className="text-2xl" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">
                    Step {stepConfig.id}: {stepConfig.name}
                  </CardTitle>
                  <Badge variant="secondary" className="font-mono text-xs">
                    {stepConfig.schedule.split(" ")[0]} {stepConfig.schedule.split(" ")[1]}
                  </Badge>
                </div>
                <CardDescription className="mt-1">
                  {stepConfig.description}
                </CardDescription>
              </div>
            </div>
            {/* Step 0: Two buttons for Ingest and AI Scoring */}
            {stepId === 0 ? (
              <div className="flex gap-2">
                <Button
                  className="gap-2"
                  onClick={() => handleRunNow("ingest")}
                  disabled={isRunning || isAiScoringRunning}
                >
                  <MaterialIcon
                    name={isRunning ? "sync" : "download"}
                    className={`text-lg ${isRunning ? "animate-spin" : ""}`}
                  />
                  {isRunning ? `Ingesting... ${elapsedTime}s` : "Ingest Articles"}
                </Button>
                <Button
                  className="gap-2"
                  variant="secondary"
                  onClick={() => handleRunNow("ai_scoring")}
                  disabled={isRunning || isAiScoringRunning}
                >
                  <MaterialIcon
                    name={isAiScoringRunning ? "sync" : "psychology"}
                    className={`text-lg ${isAiScoringRunning ? "animate-spin" : ""}`}
                  />
                  {isAiScoringRunning ? `Scoring... ${aiScoringElapsedTime}s` : "Run AI Scoring"}
                </Button>
              </div>
            ) : (
              <Button className="gap-2" onClick={() => handleRunNow()} disabled={isRunning}>
                <MaterialIcon name={isRunning ? "sync" : "play_arrow"} className={`text-lg ${isRunning ? "animate-spin" : ""}`} />
                {isRunning ? `Running... ${elapsedTime}s` : "Run Now"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex items-center gap-8 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Last Run:</span>
              <span className="font-medium">{lastRun.date}</span>
              <span className="text-muted-foreground">|</span>
              <span className="font-mono text-muted-foreground">{lastRun.duration}</span>
              <span className="text-muted-foreground">|</span>
              <StatusBadge status={lastRun.status} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Next Run:</span>
              <span className="font-medium">{nextRun}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Completion Banner */}
      {showCompletion && lastResult && (
        <Card className="border-emerald-200 bg-emerald-50/50">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100">
                  <MaterialIcon name="check_circle" className="text-xl text-emerald-600" />
                </div>
                <div>
                  <span className="font-semibold text-emerald-900">Job Completed Successfully</span>
                  <p className="text-sm text-emerald-700">
                    Processed {lastResult.processed} stories in {lastResult.elapsed}s
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {stepConfig.dataTable && (
                  <Button
                    variant="outline"
                    className="gap-2 border-emerald-300 text-emerald-700 hover:bg-emerald-100"
                    onClick={() => {
                      setActiveTab("data");
                      setShowCompletion(false);
                    }}
                  >
                    <MaterialIcon name="table_chart" className="text-base" />
                    View {stepConfig.dataTable.name}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-emerald-600 hover:bg-emerald-100"
                  onClick={() => setShowCompletion(false)}
                >
                  <MaterialIcon name="close" className="text-base" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Running Status Banner */}
      {(isRunning || isAiScoringRunning) && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardContent className="py-4">
            <div className="flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100">
                <MaterialIcon name="sync" className="text-xl text-blue-600 animate-spin" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-blue-900">
                      {currentJobType === "ai_scoring"
                        ? (aiScoringJobStatus === "queued" ? "AI Scoring Queued" : "AI Scoring Running")
                        : currentJobType === "ingest"
                        ? (jobStatus === "queued" ? "Ingest Queued" : "Ingest Running")
                        : (jobStatus === "queued" ? "Job Queued" : "Job Running")}
                    </span>
                    <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200">
                      {(currentJobType === "ai_scoring" ? aiScoringJobStatus : jobStatus) === "queued"
                        ? "Waiting for worker..."
                        : "Processing..."}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-lg font-bold text-blue-700">
                      {Math.floor((currentJobType === "ai_scoring" ? aiScoringElapsedTime : elapsedTime) / 60)}:
                      {String((currentJobType === "ai_scoring" ? aiScoringElapsedTime : elapsedTime) % 60).padStart(2, "0")}
                    </span>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={cancelJob}
                      disabled={isCancelling}
                      className="bg-red-600 hover:bg-red-700 h-8 px-3"
                    >
                      {isCancelling ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-1 h-3 w-3" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Stopping
                        </>
                      ) : (
                        <>
                          <svg className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 7.5A2.25 2.25 0 017.5 5.25h9a2.25 2.25 0 012.25 2.25v9a2.25 2.25 0 01-2.25 2.25h-9a2.25 2.25 0 01-2.25-2.25v-9z" />
                          </svg>
                          Stop
                        </>
                      )}
                    </Button>
                  </div>
                </div>
                <Progress value={undefined} className="h-2 bg-blue-100" />
                <div className="mt-2 text-sm text-blue-600">
                  <span>Job ID: {(currentJobType === "ai_scoring" ? aiScoringJobId : jobId)?.slice(0, 8)}...</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs Section */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="logs" className="gap-2">
            <MaterialIcon name="description" className="text-base" />
            Execution Logs
          </TabsTrigger>
          {stepConfig.prompts.length > 0 && (
            <TabsTrigger value="prompts" className="gap-2">
              <MaterialIcon name="psychology" className="text-base" />
              System Prompts
            </TabsTrigger>
          )}
          {stepConfig.dataTable && (
            <TabsTrigger value="data" className="gap-2">
              <MaterialIcon name="table_chart" className="text-base" />
              {stepConfig.dataTable.name}
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="logs">
          <ExecutionLogs stepId={stepId} stepName={stepConfig.name} />
        </TabsContent>

        {stepConfig.prompts.length > 0 && (
          <TabsContent value="prompts">
            <SystemPrompts stepId={stepId} prompts={stepConfig.prompts} />
          </TabsContent>
        )}

        {stepConfig.dataTable && (
          <TabsContent value="data">
            <StepData
              stepId={stepId}
              tableName={stepConfig.dataTable.name}
              tableId={stepConfig.dataTable.tableId}
              baseId={stepConfig.dataTable.baseId}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

function StatusBadge({ status }: { status: "success" | "warning" | "error" | "running" | "pending" }) {
  const config = {
    success: { icon: "check_circle", label: "OK", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    warning: { icon: "warning", label: "WARN", className: "bg-amber-100 text-amber-700 border-amber-200" },
    error: { icon: "error", label: "ERROR", className: "bg-red-100 text-red-700 border-red-200" },
    running: { icon: "sync", label: "Running", className: "bg-blue-100 text-blue-700 border-blue-200" },
    pending: { icon: "schedule", label: "Pending", className: "bg-gray-100 text-gray-600 border-gray-200" },
  }[status];

  return (
    <Badge variant="outline" className={`gap-1 ${config.className}`}>
      <MaterialIcon name={config.icon} className="text-sm" />
      {config.label}
    </Badge>
  );
}
