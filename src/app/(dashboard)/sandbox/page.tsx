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

// Sandbox job definitions
const SANDBOX_JOBS = {
  ingest_sandbox: {
    name: "Ingest from FreshRSS",
    icon: "rss_feed",
    description: "Fetch articles from FreshRSS Google Reader API"
  },
  ai_scoring_sandbox: {
    name: "AI Scoring & Extraction",
    icon: "psychology",
    description: "Score articles with Claude + extract content with Firecrawl"
  },
};

export default function SandboxPage() {
  // Ingest job state
  const [isIngestRunning, setIsIngestRunning] = useState(false);
  const [ingestJobId, setIngestJobId] = useState<string | null>(null);
  const [ingestJobStatus, setIngestJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [ingestElapsedTime, setIngestElapsedTime] = useState(0);
  const [ingestResult, setIngestResult] = useState<{ processed: number; elapsed: number } | null>(null);

  // AI Scoring job state
  const [isScoringRunning, setIsScoringRunning] = useState(false);
  const [scoringJobId, setScoringJobId] = useState<string | null>(null);
  const [scoringJobStatus, setScoringJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [scoringElapsedTime, setScoringElapsedTime] = useState(0);
  const [scoringResult, setScoringResult] = useState<{ scored: number; selects: number; elapsed: number } | null>(null);

  const [isCancelling, setIsCancelling] = useState(false);

  // Cancel running job
  const cancelJob = async (jobType: "ingest" | "scoring") => {
    const jobId = jobType === "ingest" ? ingestJobId : scoringJobId;
    if (!jobId) return;

    setIsCancelling(true);
    try {
      const response = await fetch("/api/jobs/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId }),
      });

      const data = await response.json();
      if (response.ok) {
        toast.success("Job cancelled");
        if (jobType === "ingest") {
          setIsIngestRunning(false);
          setIngestJobId(null);
          setIngestJobStatus(null);
        } else {
          setIsScoringRunning(false);
          setScoringJobId(null);
          setScoringJobStatus(null);
        }
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

  // Trigger a sandbox job
  const runJob = async (jobType: "ingest" | "scoring") => {
    const jobName = jobType === "ingest" ? "ingest_sandbox" : "ai_scoring_sandbox";
    const jobConfig = jobType === "ingest" ? SANDBOX_JOBS.ingest_sandbox : SANDBOX_JOBS.ai_scoring_sandbox;

    if (jobType === "ingest") {
      setIsIngestRunning(true);
      setIngestElapsedTime(0);
      setIngestResult(null);
    } else {
      setIsScoringRunning(true);
      setScoringElapsedTime(0);
      setScoringResult(null);
    }

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: jobName }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (jobType === "ingest") {
          setIngestJobId(data.job_id);
          setIngestJobStatus("queued");
        } else {
          setScoringJobId(data.job_id);
          setScoringJobStatus("queued");
        }
        toast.success("Job Started", {
          description: `${jobConfig.name} job queued successfully`,
        });
      } else {
        if (jobType === "ingest") {
          setIsIngestRunning(false);
        } else {
          setIsScoringRunning(false);
        }
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      if (jobType === "ingest") {
        setIsIngestRunning(false);
      } else {
        setIsScoringRunning(false);
      }
      toast.error("Error", {
        description: error instanceof Error ? error.message : "Failed to start job",
      });
    }
  };

  // Poll ingest job status
  useEffect(() => {
    if (!ingestJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setIngestElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${ingestJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setIngestJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsIngestRunning(false);
          setIngestJobId(null);
          setIngestJobStatus(status.status);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const processedCount = status.result?.articles_ingested || status.result?.processed || 0;
            setIngestResult({ processed: processedCount, elapsed: finalElapsed });
            toast.success("Ingest Completed", {
              description: `Ingested ${processedCount} articles in ${finalElapsed}s`,
            });
          } else {
            toast.error("Ingest Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling ingest job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [ingestJobId]);

  // Poll AI Scoring job status
  useEffect(() => {
    if (!scoringJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setScoringElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${scoringJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setScoringJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsScoringRunning(false);
          setScoringJobId(null);
          setScoringJobStatus(status.status);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const scoredCount = status.result?.articles_scored || 0;
            const selectsCreated = status.result?.newsletter_selects_created || 0;
            setScoringResult({ scored: scoredCount, selects: selectsCreated, elapsed: finalElapsed });
            toast.success("AI Scoring Completed", {
              description: `Scored ${scoredCount} articles, created ${selectsCreated} Newsletter Selects in ${finalElapsed}s`,
            });
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
  }, [scoringJobId]);

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
              <MaterialIcon name="science" className="text-2xl" />
            </div>
            <div>
              <CardTitle className="text-xl">FreshRSS Sandbox Pipeline</CardTitle>
              <CardDescription className="mt-1">
                Test ingestion engine with FreshRSS feeds → AI Scoring → Newsletter Selects
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Pipeline Steps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Step 1: Ingest from FreshRSS */}
        <Card className={isIngestRunning ? "border-blue-200 bg-blue-50/30" : ""}>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                isIngestRunning ? "bg-blue-100 text-blue-600" : "bg-orange-100 text-orange-600"
              }`}>
                <MaterialIcon name={SANDBOX_JOBS.ingest_sandbox.icon} className="text-xl" />
              </div>
              <div>
                <CardTitle className="text-base">{SANDBOX_JOBS.ingest_sandbox.name}</CardTitle>
                <CardDescription className="text-xs">
                  {SANDBOX_JOBS.ingest_sandbox.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isIngestRunning ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200">
                    {ingestJobStatus === "queued" ? "Queued..." : "Running..."}
                  </Badge>
                  <span className="font-mono text-lg font-bold text-blue-700">
                    {Math.floor(ingestElapsedTime / 60)}:{String(ingestElapsedTime % 60).padStart(2, "0")}
                  </span>
                </div>
                <Progress value={undefined} className="h-2 bg-blue-100" />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-blue-600">Job ID: {ingestJobId?.slice(0, 8)}...</span>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => cancelJob("ingest")}
                    disabled={isCancelling}
                    className="h-7 px-2 text-xs"
                  >
                    {isCancelling ? "Stopping..." : "Stop"}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {ingestResult && (
                  <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-md px-3 py-2">
                    <MaterialIcon name="check_circle" className="text-base" />
                    <span>Ingested {ingestResult.processed} articles in {ingestResult.elapsed}s</span>
                  </div>
                )}
                <Button
                  onClick={() => runJob("ingest")}
                  disabled={isScoringRunning}
                  className="w-full gap-2"
                >
                  <MaterialIcon name="rss_feed" className="text-lg" />
                  Run Ingest
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 2: AI Scoring + Extraction */}
        <Card className={isScoringRunning ? "border-blue-200 bg-blue-50/30" : ""}>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                isScoringRunning ? "bg-blue-100 text-blue-600" : "bg-violet-100 text-violet-600"
              }`}>
                <MaterialIcon name={SANDBOX_JOBS.ai_scoring_sandbox.icon} className="text-xl" />
              </div>
              <div>
                <CardTitle className="text-base">{SANDBOX_JOBS.ai_scoring_sandbox.name}</CardTitle>
                <CardDescription className="text-xs">
                  {SANDBOX_JOBS.ai_scoring_sandbox.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isScoringRunning ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200">
                    {scoringJobStatus === "queued" ? "Queued..." : "Running..."}
                  </Badge>
                  <span className="font-mono text-lg font-bold text-blue-700">
                    {Math.floor(scoringElapsedTime / 60)}:{String(scoringElapsedTime % 60).padStart(2, "0")}
                  </span>
                </div>
                <Progress value={undefined} className="h-2 bg-blue-100" />
                <div className="flex items-center justify-between">
                  <span className="text-xs text-blue-600">Job ID: {scoringJobId?.slice(0, 8)}...</span>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => cancelJob("scoring")}
                    disabled={isCancelling}
                    className="h-7 px-2 text-xs"
                  >
                    {isCancelling ? "Stopping..." : "Stop"}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {scoringResult && (
                  <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-md px-3 py-2">
                    <MaterialIcon name="check_circle" className="text-base" />
                    <span>Scored {scoringResult.scored}, created {scoringResult.selects} selects in {scoringResult.elapsed}s</span>
                  </div>
                )}
                <Button
                  onClick={() => runJob("scoring")}
                  disabled={isIngestRunning}
                  className="w-full gap-2"
                  variant="secondary"
                >
                  <MaterialIcon name="psychology" className="text-lg" />
                  Run AI Scoring
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Info Card */}
      <Card className="border-amber-200 bg-amber-50/50">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <MaterialIcon name="info" className="text-xl text-amber-600 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium mb-1">Sandbox Pipeline Flow:</p>
              <ol className="list-decimal list-inside space-y-1 text-amber-700">
                <li><strong>Ingest:</strong> Fetches articles from FreshRSS → saves to &quot;Articles - All Ingested&quot;</li>
                <li><strong>AI Scoring:</strong> Scores with Claude → extracts content with Firecrawl → creates &quot;Newsletter Selects&quot; for high-interest articles</li>
              </ol>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
