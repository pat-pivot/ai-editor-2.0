"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Import,
  Download,
  Brain,
  Link2,
  Rss,
  Loader2,
  Square,
  Timer,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle
} from "lucide-react";
import { formatDateET, formatDuration } from "@/lib/date-utils";
import { ArticlesTable } from "./articles-table";
import { NewsletterSelectsTable } from "./newsletter-selects-table";
import { LiveExecutionLogs } from "./live-execution-logs";

// Status badge component for last run status
function StatusBadge({ status }: { status: "success" | "failed" | "running" }) {
  const config = {
    success: { Icon: CheckCircle, label: "OK", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    failed: { Icon: XCircle, label: "ERROR", className: "bg-red-100 text-red-700 border-red-200" },
    running: { Icon: Loader2, label: "Running", className: "bg-blue-100 text-blue-700 border-blue-200" },
  }[status];

  return (
    <Badge variant="outline" className={`gap-1 ${config.className}`}>
      <config.Icon className={`h-3 w-3 ${status === "running" ? "animate-spin" : ""}`} />
      {config.label}
    </Badge>
  );
}

// Zeroin job definitions
const ZEROIN_JOBS = {
  ingest_sandbox: {
    name: "Ingest Articles",
    icon: Download,
    description: "Fetch articles from FreshRSS feeds"
  },
  ai_scoring_sandbox: {
    name: "AI Scoring",
    icon: Brain,
    description: "Score articles with Claude + extract with Firecrawl"
  },
  newsletter_extract_sandbox: {
    name: "Newsletter Links",
    icon: Link2,
    description: "Extract news links from newsletters via Claude Haiku"
  },
  ingest_direct_feeds: {
    name: "Direct Feed Ingest",
    icon: Rss,
    description: "Ingest non-Google News RSS feeds (Reuters, TechCrunch, etc.)"
  },
};

export function ZeroinIngestPanel() {
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

  // Newsletter Extraction job state
  const [isNewsletterRunning, setIsNewsletterRunning] = useState(false);
  const [newsletterJobId, setNewsletterJobId] = useState<string | null>(null);
  const [newsletterJobStatus, setNewsletterJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [newsletterElapsedTime, setNewsletterElapsedTime] = useState(0);
  const [newsletterResult, setNewsletterResult] = useState<{ processed: number; elapsed: number } | null>(null);

  // Direct Feed Ingest job state
  const [isDirectFeedRunning, setIsDirectFeedRunning] = useState(false);
  const [directFeedJobId, setDirectFeedJobId] = useState<string | null>(null);
  const [directFeedJobStatus, setDirectFeedJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [directFeedElapsedTime, setDirectFeedElapsedTime] = useState(0);
  const [directFeedResult, setDirectFeedResult] = useState<{ processed: number; elapsed: number } | null>(null);

  const [isCancelling, setIsCancelling] = useState(false);

  // Tab state
  const [activeTab, setActiveTab] = useState("jobs");

  // Last run tracking
  interface LastRunInfo {
    timestamp: string;
    duration_seconds: number;
    status: "success" | "failed" | "running";
  }
  const [lastRunIngest, setLastRunIngest] = useState<LastRunInfo | null>(null);
  const [lastRunScoring, setLastRunScoring] = useState<LastRunInfo | null>(null);
  const [lastRunNewsletter, setLastRunNewsletter] = useState<LastRunInfo | null>(null);
  const [lastRunDirectFeed, setLastRunDirectFeed] = useState<LastRunInfo | null>(null);

  // Fetch last run data on mount
  useEffect(() => {
    const fetchLastRuns = async () => {
      try {
        const [ingestRes, scoringRes, newsletterRes, directFeedRes] = await Promise.all([
          fetch("/api/jobs/last-run?step=ingest_sandbox"),
          fetch("/api/jobs/last-run?step=ai_scoring_sandbox"),
          fetch("/api/jobs/last-run?step=newsletter_extract_sandbox"),
          fetch("/api/jobs/last-run?step=ingest_direct_feeds"),
        ]);

        if (ingestRes.ok) {
          const data = await ingestRes.json();
          if (data.last_run) setLastRunIngest(data.last_run);
        }
        if (scoringRes.ok) {
          const data = await scoringRes.json();
          if (data.last_run) setLastRunScoring(data.last_run);
        }
        if (newsletterRes.ok) {
          const data = await newsletterRes.json();
          if (data.last_run) setLastRunNewsletter(data.last_run);
        }
        if (directFeedRes.ok) {
          const data = await directFeedRes.json();
          if (data.last_run) setLastRunDirectFeed(data.last_run);
        }
      } catch (error) {
        console.error("Error fetching last run data:", error);
      }
    };

    fetchLastRuns();
  }, []);

  // Cancel running job
  const cancelJob = async (jobType: "ingest" | "scoring" | "newsletter" | "directfeed") => {
    const jobId = jobType === "ingest" ? ingestJobId : jobType === "scoring" ? scoringJobId : jobType === "newsletter" ? newsletterJobId : directFeedJobId;
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
        } else if (jobType === "scoring") {
          setIsScoringRunning(false);
          setScoringJobId(null);
          setScoringJobStatus(null);
        } else if (jobType === "newsletter") {
          setIsNewsletterRunning(false);
          setNewsletterJobId(null);
          setNewsletterJobStatus(null);
        } else {
          setIsDirectFeedRunning(false);
          setDirectFeedJobId(null);
          setDirectFeedJobStatus(null);
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
  const runJob = async (jobType: "ingest" | "scoring" | "newsletter" | "directfeed") => {
    const jobName = jobType === "ingest" ? "ingest_sandbox"
      : jobType === "scoring" ? "ai_scoring_sandbox"
      : jobType === "newsletter" ? "newsletter_extract_sandbox"
      : "ingest_direct_feeds";
    const jobConfig = jobType === "ingest" ? ZEROIN_JOBS.ingest_sandbox
      : jobType === "scoring" ? ZEROIN_JOBS.ai_scoring_sandbox
      : jobType === "newsletter" ? ZEROIN_JOBS.newsletter_extract_sandbox
      : ZEROIN_JOBS.ingest_direct_feeds;

    if (jobType === "ingest") {
      setIsIngestRunning(true);
      setIngestElapsedTime(0);
      setIngestResult(null);
    } else if (jobType === "scoring") {
      setIsScoringRunning(true);
      setScoringElapsedTime(0);
      setScoringResult(null);
    } else if (jobType === "newsletter") {
      setIsNewsletterRunning(true);
      setNewsletterElapsedTime(0);
      setNewsletterResult(null);
    } else {
      setIsDirectFeedRunning(true);
      setDirectFeedElapsedTime(0);
      setDirectFeedResult(null);
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
        } else if (jobType === "scoring") {
          setScoringJobId(data.job_id);
          setScoringJobStatus("queued");
        } else if (jobType === "newsletter") {
          setNewsletterJobId(data.job_id);
          setNewsletterJobStatus("queued");
        } else {
          setDirectFeedJobId(data.job_id);
          setDirectFeedJobStatus("queued");
        }
        toast.success("Job Started", {
          description: `${jobConfig.name} job queued`,
        });
      } else {
        if (jobType === "ingest") {
          setIsIngestRunning(false);
        } else if (jobType === "scoring") {
          setIsScoringRunning(false);
        } else if (jobType === "newsletter") {
          setIsNewsletterRunning(false);
        } else {
          setIsDirectFeedRunning(false);
        }
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      if (jobType === "ingest") {
        setIsIngestRunning(false);
      } else if (jobType === "scoring") {
        setIsScoringRunning(false);
      } else if (jobType === "newsletter") {
        setIsNewsletterRunning(false);
      } else {
        setIsDirectFeedRunning(false);
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
              description: `Scored ${scoredCount} articles, created ${selectsCreated} selects in ${finalElapsed}s`,
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

  // Poll Newsletter Extraction job status
  useEffect(() => {
    if (!newsletterJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setNewsletterElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${newsletterJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setNewsletterJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsNewsletterRunning(false);
          setNewsletterJobId(null);
          setNewsletterJobStatus(status.status);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const processedCount = status.result?.records_created || status.result?.processed || 0;
            setNewsletterResult({ processed: processedCount, elapsed: finalElapsed });
            toast.success("Newsletter Extraction Completed", {
              description: `Extracted ${processedCount} links in ${finalElapsed}s`,
            });
          } else {
            toast.error("Newsletter Extraction Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling Newsletter Extraction job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [newsletterJobId]);

  // Poll Direct Feed Ingest job status
  useEffect(() => {
    if (!directFeedJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setDirectFeedElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${directFeedJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setDirectFeedJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsDirectFeedRunning(false);
          setDirectFeedJobId(null);
          setDirectFeedJobStatus(status.status);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const processedCount = status.result?.articles_ingested || status.result?.processed || 0;
            setDirectFeedResult({ processed: processedCount, elapsed: finalElapsed });
            toast.success("Direct Feed Ingest Completed", {
              description: `Ingested ${processedCount} articles in ${finalElapsed}s`,
            });
          } else {
            toast.error("Direct Feed Ingest Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling Direct Feed Ingest job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [directFeedJobId]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, "0")}`;
  };

  // Calculate the most recent last run across all jobs for the header
  const getMostRecentLastRun = () => {
    const runs = [lastRunIngest, lastRunScoring, lastRunNewsletter].filter(Boolean) as LastRunInfo[];
    if (runs.length === 0) return null;

    return runs.reduce((mostRecent, current) => {
      const currentTime = new Date(current.timestamp).getTime();
      const mostRecentTime = new Date(mostRecent.timestamp).getTime();
      return currentTime > mostRecentTime ? current : mostRecent;
    });
  };

  // Next run calculation - Step 0 Ingest runs at 8:00 PM ET Monday-Friday
  const getNextRunDisplay = () => {
    const scheduledHour = 20; // 8:00 PM

    const now = new Date();
    const etNow = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
    const currentHour = etNow.getHours();
    const currentDay = etNow.getDay(); // 0 = Sunday, 6 = Saturday

    // Check if we should run today (Mon-Fri and before 8 PM)
    const isWeekday = currentDay >= 1 && currentDay <= 5;

    if (isWeekday && currentHour < scheduledHour) {
      const nextRun = new Date(etNow);
      nextRun.setHours(scheduledHour, 0, 0, 0);
      return formatDateET(nextRun);
    }

    // Find next weekday
    const nextRun = new Date(etNow);
    let daysToAdd = 1;

    if (currentDay === 5) {
      // Friday after 8 PM -> Monday
      daysToAdd = 3;
    } else if (currentDay === 6) {
      // Saturday -> Monday
      daysToAdd = 2;
    } else if (currentDay === 0) {
      // Sunday -> Monday
      daysToAdd = 1;
    }

    nextRun.setDate(nextRun.getDate() + daysToAdd);
    nextRun.setHours(scheduledHour, 0, 0, 0);
    return formatDateET(nextRun);
  };

  const mostRecentRun = getMostRecentLastRun();

  // Render last run info for a job
  const renderLastRun = (lastRun: LastRunInfo | null) => {
    if (!lastRun) return null;

    const StatusIcon = lastRun.status === "success" ? CheckCircle : lastRun.status === "failed" ? XCircle : Clock;
    const statusColor = lastRun.status === "success" ? "text-green-600" : lastRun.status === "failed" ? "text-red-500" : "text-orange-500";

    return (
      <div className="flex items-center gap-2 text-xs text-zinc-500 mt-2 pt-2 border-t border-zinc-100">
        <Clock className="h-3 w-3 flex-shrink-0" />
        <span className="truncate">{formatDateET(lastRun.timestamp)}</span>
        <span className="text-zinc-300">|</span>
        <span className="font-mono">{formatDuration(lastRun.duration_seconds)}</span>
        <StatusIcon className={`h-3 w-3 ${statusColor} flex-shrink-0`} />
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Step Header Card - matching Step 1 Pre-filter design */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-orange-100 text-orange-600">
                <Import className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">
                    Step 0: Ingest
                  </CardTitle>
                  <Badge variant="secondary" className="font-mono text-xs">
                    8:00 PM ET
                  </Badge>
                </div>
                <CardDescription className="mt-1">
                  Fetch articles from RSS feeds, score with AI, extract newsletter links
                </CardDescription>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex items-center gap-8 text-sm">
            {mostRecentRun ? (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Last Run:</span>
                <span className="font-medium">{formatDateET(mostRecentRun.timestamp)}</span>
                <span className="text-muted-foreground">|</span>
                <span className="font-mono text-muted-foreground">{formatDuration(mostRecentRun.duration_seconds)}</span>
                <span className="text-muted-foreground">|</span>
                <StatusBadge status={mostRecentRun.status === "failed" ? "failed" : mostRecentRun.status} />
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Last Run:</span>
                <span className="text-muted-foreground italic">No recent runs</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Next Run:</span>
              <span className="font-medium">{getNextRunDisplay()}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs for Jobs, Articles, and Newsletter Selects */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-zinc-100">
          <TabsTrigger value="jobs" className="data-[state=active]:bg-white">
            Jobs
          </TabsTrigger>
          <TabsTrigger value="articles" className="data-[state=active]:bg-white">
            Articles All Ingested
          </TabsTrigger>
          <TabsTrigger value="newsletter" className="data-[state=active]:bg-white">
            Newsletter Selects
          </TabsTrigger>
        </TabsList>

        {/* Jobs Tab Content */}
        <TabsContent value="jobs" className="space-y-6">
          {/* Pipeline Steps */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Step 1: Ingest */}
        <Card className={`transition-all duration-200 ${isIngestRunning ? "ring-2 ring-orange-500 ring-offset-2" : "hover:shadow-md"}`}>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                isIngestRunning ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-600"
              }`}>
                {isIngestRunning ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Download className="h-5 w-5" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <CardTitle className="text-sm font-medium">{ZEROIN_JOBS.ingest_sandbox.name}</CardTitle>
                <CardDescription className="text-xs truncate">
                  {ZEROIN_JOBS.ingest_sandbox.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {isIngestRunning ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="bg-orange-100 text-orange-700 hover:bg-orange-100">
                    {ingestJobStatus === "queued" ? "Queued" : "Running"}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-orange-600">
                    <Timer className="h-3.5 w-3.5" />
                    <span className="font-mono text-sm font-medium">
                      {formatTime(ingestElapsedTime)}
                    </span>
                  </div>
                </div>
                <Progress value={undefined} className="h-1.5" />
                <div className="flex items-center justify-between">
                  <code className="text-[10px] text-zinc-400">{ingestJobId?.slice(0, 8)}</code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => cancelJob("ingest")}
                    disabled={isCancelling}
                    className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                  >
                    <Square className="h-3 w-3 mr-1" />
                    Stop
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {ingestResult && (
                  <div className="text-xs text-zinc-600 bg-zinc-50 rounded-lg px-3 py-2">
                    <span>{ingestResult.processed} articles in {ingestResult.elapsed}s</span>
                  </div>
                )}
                <Button
                  onClick={() => runJob("ingest")}
                  disabled={isScoringRunning || isNewsletterRunning}
                  className="w-full bg-orange-500 hover:bg-orange-600 text-white"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Run Ingest
                </Button>
                {renderLastRun(lastRunIngest)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 2: AI Scoring */}
        <Card className={`transition-all duration-200 ${isScoringRunning ? "ring-2 ring-orange-500 ring-offset-2" : "hover:shadow-md"}`}>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                isScoringRunning ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-600"
              }`}>
                {isScoringRunning ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Brain className="h-5 w-5" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <CardTitle className="text-sm font-medium">{ZEROIN_JOBS.ai_scoring_sandbox.name}</CardTitle>
                <CardDescription className="text-xs truncate">
                  {ZEROIN_JOBS.ai_scoring_sandbox.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {isScoringRunning ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="bg-orange-100 text-orange-700 hover:bg-orange-100">
                    {scoringJobStatus === "queued" ? "Queued" : "Running"}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-orange-600">
                    <Timer className="h-3.5 w-3.5" />
                    <span className="font-mono text-sm font-medium">
                      {formatTime(scoringElapsedTime)}
                    </span>
                  </div>
                </div>
                <Progress value={undefined} className="h-1.5" />
                <div className="flex items-center justify-between">
                  <code className="text-[10px] text-zinc-400">{scoringJobId?.slice(0, 8)}</code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => cancelJob("scoring")}
                    disabled={isCancelling}
                    className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                  >
                    <Square className="h-3 w-3 mr-1" />
                    Stop
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {scoringResult && (
                  <div className="text-xs text-zinc-600 bg-zinc-50 rounded-lg px-3 py-2">
                    <span>{scoringResult.scored} scored, {scoringResult.selects} selects</span>
                  </div>
                )}
                <Button
                  onClick={() => runJob("scoring")}
                  disabled={isIngestRunning || isNewsletterRunning}
                  variant="outline"
                  className="w-full border-orange-200 text-orange-600 hover:bg-orange-50 hover:text-orange-700"
                >
                  <Brain className="h-4 w-4 mr-2" />
                  Run Scoring
                </Button>
                {renderLastRun(lastRunScoring)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 3: Newsletter Links */}
        <Card className={`transition-all duration-200 ${isNewsletterRunning ? "ring-2 ring-orange-500 ring-offset-2" : "hover:shadow-md"}`}>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                isNewsletterRunning ? "bg-orange-500 text-white" : "bg-orange-100 text-orange-600"
              }`}>
                {isNewsletterRunning ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Link2 className="h-5 w-5" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <CardTitle className="text-sm font-medium">{ZEROIN_JOBS.newsletter_extract_sandbox.name}</CardTitle>
                <CardDescription className="text-xs truncate">
                  {ZEROIN_JOBS.newsletter_extract_sandbox.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {isNewsletterRunning ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="bg-orange-100 text-orange-700 hover:bg-orange-100">
                    {newsletterJobStatus === "queued" ? "Queued" : "Running"}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-orange-600">
                    <Timer className="h-3.5 w-3.5" />
                    <span className="font-mono text-sm font-medium">
                      {formatTime(newsletterElapsedTime)}
                    </span>
                  </div>
                </div>
                <Progress value={undefined} className="h-1.5" />
                <div className="flex items-center justify-between">
                  <code className="text-[10px] text-zinc-400">{newsletterJobId?.slice(0, 8)}</code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => cancelJob("newsletter")}
                    disabled={isCancelling}
                    className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                  >
                    <Square className="h-3 w-3 mr-1" />
                    Stop
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {newsletterResult && (
                  <div className="text-xs text-zinc-600 bg-zinc-50 rounded-lg px-3 py-2">
                    <span>{newsletterResult.processed} links in {newsletterResult.elapsed}s</span>
                  </div>
                )}
                <Button
                  onClick={() => runJob("newsletter")}
                  disabled={isIngestRunning || isScoringRunning}
                  variant="outline"
                  className="w-full border-orange-200 text-orange-600 hover:bg-orange-50 hover:text-orange-700"
                >
                  <Link2 className="h-4 w-4 mr-2" />
                  Extract Links
                </Button>
                {renderLastRun(lastRunNewsletter)}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 4: Direct Feed Ingest */}
        <Card className={`transition-all duration-200 ${isDirectFeedRunning ? "ring-2 ring-teal-500 ring-offset-2" : "hover:shadow-md"}`}>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg transition-colors ${
                isDirectFeedRunning ? "bg-teal-500 text-white" : "bg-teal-100 text-teal-600"
              }`}>
                {isDirectFeedRunning ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Rss className="h-5 w-5" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <CardTitle className="text-sm font-medium">{ZEROIN_JOBS.ingest_direct_feeds.name}</CardTitle>
                <CardDescription className="text-xs truncate">
                  {ZEROIN_JOBS.ingest_direct_feeds.description}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {isDirectFeedRunning ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="secondary" className="bg-teal-100 text-teal-700 hover:bg-teal-100">
                    {directFeedJobStatus === "queued" ? "Queued" : "Running"}
                  </Badge>
                  <div className="flex items-center gap-1.5 text-teal-600">
                    <Timer className="h-3.5 w-3.5" />
                    <span className="font-mono text-sm font-medium">
                      {formatTime(directFeedElapsedTime)}
                    </span>
                  </div>
                </div>
                <Progress value={undefined} className="h-1.5" />
                <div className="flex items-center justify-between">
                  <code className="text-[10px] text-zinc-400">{directFeedJobId?.slice(0, 8)}</code>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => cancelJob("directfeed")}
                    disabled={isCancelling}
                    className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                  >
                    <Square className="h-3 w-3 mr-1" />
                    Stop
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {directFeedResult && (
                  <div className="text-xs text-zinc-600 bg-zinc-50 rounded-lg px-3 py-2">
                    <span>{directFeedResult.processed} articles in {directFeedResult.elapsed}s</span>
                  </div>
                )}
                <Button
                  onClick={() => runJob("directfeed")}
                  disabled={isIngestRunning || isScoringRunning || isNewsletterRunning}
                  variant="outline"
                  className="w-full border-teal-200 text-teal-600 hover:bg-teal-50 hover:text-teal-700"
                >
                  <Rss className="h-4 w-4 mr-2" />
                  Run Direct Feeds
                </Button>
                {renderLastRun(lastRunDirectFeed)}
              </div>
            )}
          </CardContent>
        </Card>
          </div>

        </TabsContent>

        {/* Articles All Ingested Tab Content */}
        <TabsContent value="articles">
          <ArticlesTable />
        </TabsContent>

        {/* Newsletter Selects Tab Content */}
        <TabsContent value="newsletter">
          <NewsletterSelectsTable />
        </TabsContent>
      </Tabs>

      {/* Execution Logs Section - Live from Render API */}
      <LiveExecutionLogs stepId={0} title="Step 0: Ingest Logs" />
    </div>
  );
}
