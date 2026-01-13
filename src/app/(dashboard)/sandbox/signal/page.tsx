"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Zap,
  CheckSquare,
  Sparkles,
  Code,
  CheckCircle,
  Loader2,
  Square,
  Info,
  Timer,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

// Signal job definitions
const SIGNAL_JOBS = {
  signal_slot_selection: {
    name: "Slot Selection",
    icon: CheckSquare,
    description: "Select stories for Signal newsletter (1 top, 3 features, 5 signals)",
    color: "purple",
  },
  signal_decoration: {
    name: "Decoration",
    icon: Sparkles,
    description: "Generate headlines, deks, and summaries for Signal stories",
    color: "blue",
  },
  signal_html_compile: {
    name: "HTML Compile",
    icon: Code,
    description: "Compile Signal newsletter HTML (text-only, no images)",
    color: "emerald",
  },
};

interface JobState {
  isRunning: boolean;
  jobId: string | null;
  jobStatus: "queued" | "started" | "finished" | "failed" | null;
  elapsedTime: number;
  result: Record<string, unknown> | null;
}

interface SlotData {
  id: string;
  issue_number?: number;
  status?: string;
  top_story?: string;
  ai_at_work?: string;
  emerging?: string;
  beyond?: string;
  signal_1?: string;
  signal_2?: string;
  signal_3?: string;
  signal_4?: string;
  signal_5?: string;
  [key: string]: unknown;
}

interface DecorationData {
  id: string;
  section: string;
  story_id?: string;
  ai_headline?: string;
  ai_dek?: string;
  signal_summary?: string;
  signalNum?: number;
  [key: string]: unknown;
}

export default function SignalSandboxPage() {
  const [activeTab, setActiveTab] = useState("slot_selection");

  // Job states for each step
  const [slotSelectionState, setSlotSelectionState] = useState<JobState>({
    isRunning: false,
    jobId: null,
    jobStatus: null,
    elapsedTime: 0,
    result: null,
  });

  const [decorationState, setDecorationState] = useState<JobState>({
    isRunning: false,
    jobId: null,
    jobStatus: null,
    elapsedTime: 0,
    result: null,
  });

  const [htmlCompileState, setHtmlCompileState] = useState<JobState>({
    isRunning: false,
    jobId: null,
    jobStatus: null,
    elapsedTime: 0,
    result: null,
  });

  // Data states
  const [slotData, setSlotData] = useState<SlotData | null>(null);
  const [decorationData, setDecorationData] = useState<DecorationData[]>([]);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isLoadingDecorations, setIsLoadingDecorations] = useState(false);

  const [isCancelling, setIsCancelling] = useState(false);

  // Fetch slot data
  const fetchSlotData = async (skipCache = false) => {
    setIsLoadingSlots(true);
    try {
      const url = skipCache ? "/api/signal/slots?skipCache=true" : "/api/signal/slots";
      const response = await fetch(url);
      const data = await response.json();
      if (data.selectedSlots) {
        setSlotData(data.selectedSlots);
      } else {
        setSlotData(null);
      }
    } catch (error) {
      console.error("Error fetching slot data:", error);
      toast.error("Failed to fetch slot data");
    } finally {
      setIsLoadingSlots(false);
    }
  };

  // Fetch decoration data
  const fetchDecorationData = async (issueId: string, skipCache = false) => {
    setIsLoadingDecorations(true);
    try {
      const url = `/api/signal/decorations?issueId=${issueId}${skipCache ? "&skipCache=true" : ""}`;
      const response = await fetch(url);
      const data = await response.json();
      if (data.decorations) {
        setDecorationData(data.decorations);
      }
    } catch (error) {
      console.error("Error fetching decoration data:", error);
      toast.error("Failed to fetch decoration data");
    } finally {
      setIsLoadingDecorations(false);
    }
  };

  // Load slot data on mount
  useEffect(() => {
    fetchSlotData();
  }, []);

  // Cancel running job
  const cancelJob = async (jobType: "slot_selection" | "decoration" | "html_compile") => {
    const state = jobType === "slot_selection" ? slotSelectionState :
                  jobType === "decoration" ? decorationState : htmlCompileState;
    if (!state.jobId) return;

    setIsCancelling(true);
    try {
      const response = await fetch("/api/jobs/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId: state.jobId }),
      });

      const data = await response.json();
      if (response.ok) {
        toast.success("Job cancelled");
        const resetState = {
          isRunning: false,
          jobId: null,
          jobStatus: null,
        };
        if (jobType === "slot_selection") {
          setSlotSelectionState(prev => ({ ...prev, ...resetState }));
        } else if (jobType === "decoration") {
          setDecorationState(prev => ({ ...prev, ...resetState }));
        } else {
          setHtmlCompileState(prev => ({ ...prev, ...resetState }));
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

  // Trigger a job
  const runJob = async (jobType: "slot_selection" | "decoration" | "html_compile") => {
    const jobName = `signal_${jobType}`;
    const setState = jobType === "slot_selection" ? setSlotSelectionState :
                     jobType === "decoration" ? setDecorationState : setHtmlCompileState;

    setState(prev => ({
      ...prev,
      isRunning: true,
      elapsedTime: 0,
      result: null,
    }));

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: jobName }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setState(prev => ({
          ...prev,
          jobId: data.job_id,
          jobStatus: "queued",
        }));
        toast.success("Job Started", {
          description: `${SIGNAL_JOBS[jobName as keyof typeof SIGNAL_JOBS].name} job queued`,
        });
      } else {
        setState(prev => ({ ...prev, isRunning: false }));
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      setState(prev => ({ ...prev, isRunning: false }));
      toast.error("Error", {
        description: error instanceof Error ? error.message : "Failed to start job",
      });
    }
  };

  // Poll job status for slot selection
  useEffect(() => {
    if (!slotSelectionState.jobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setSlotSelectionState(prev => ({
        ...prev,
        elapsedTime: Math.floor((Date.now() - startTime) / 1000),
      }));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${slotSelectionState.jobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setSlotSelectionState(prev => ({ ...prev, jobStatus: status.status }));
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            setSlotSelectionState(prev => ({
              ...prev,
              isRunning: false,
              jobId: null,
              jobStatus: "finished",
              result: status.result,
            }));
            toast.success("Slot Selection Completed", {
              description: `Selected stories in ${finalElapsed}s`,
            });
            // Refresh slot data
            fetchSlotData(true);
          } else {
            setSlotSelectionState(prev => ({
              ...prev,
              isRunning: false,
              jobId: null,
              jobStatus: "failed",
            }));
            toast.error("Slot Selection Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling slot selection job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [slotSelectionState.jobId]);

  // Poll job status for decoration
  useEffect(() => {
    if (!decorationState.jobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setDecorationState(prev => ({
        ...prev,
        elapsedTime: Math.floor((Date.now() - startTime) / 1000),
      }));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${decorationState.jobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setDecorationState(prev => ({ ...prev, jobStatus: status.status }));
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            setDecorationState(prev => ({
              ...prev,
              isRunning: false,
              jobId: null,
              jobStatus: "finished",
              result: status.result,
            }));
            toast.success("Decoration Completed", {
              description: `Decorated stories in ${finalElapsed}s`,
            });
            // Refresh decoration data if we have an issue ID
            if (slotData?.id) {
              fetchDecorationData(slotData.id, true);
            }
          } else {
            setDecorationState(prev => ({
              ...prev,
              isRunning: false,
              jobId: null,
              jobStatus: "failed",
            }));
            toast.error("Decoration Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling decoration job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [decorationState.jobId, slotData?.id]);

  // Poll job status for HTML compile
  useEffect(() => {
    if (!htmlCompileState.jobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setHtmlCompileState(prev => ({
        ...prev,
        elapsedTime: Math.floor((Date.now() - startTime) / 1000),
      }));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${htmlCompileState.jobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setHtmlCompileState(prev => ({ ...prev, jobStatus: status.status }));
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            setHtmlCompileState(prev => ({
              ...prev,
              isRunning: false,
              jobId: null,
              jobStatus: "finished",
              result: status.result,
            }));
            toast.success("HTML Compile Completed", {
              description: `Compiled newsletter in ${finalElapsed}s`,
            });
          } else {
            setHtmlCompileState(prev => ({
              ...prev,
              isRunning: false,
              jobId: null,
              jobStatus: "failed",
            }));
            toast.error("HTML Compile Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling HTML compile job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [htmlCompileState.jobId]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${String(secs).padStart(2, "0")}`;
  };

  const anyJobRunning = slotSelectionState.isRunning || decorationState.isRunning || htmlCompileState.isRunning;

  // Slot display labels
  const SLOT_LABELS: Record<string, string> = {
    top_story: "TOP STORY",
    ai_at_work: "AI AT WORK",
    emerging: "EMERGING MOVES",
    beyond: "BEYOND BUSINESS",
    signal_1: "SIGNAL 1",
    signal_2: "SIGNAL 2",
    signal_3: "SIGNAL 3",
    signal_4: "SIGNAL 4",
    signal_5: "SIGNAL 5",
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-500 text-white shadow-lg shadow-purple-500/25">
          <Zap className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900">Signal Newsletter</h1>
          <p className="text-sm text-zinc-500">
            Text-only newsletter: Slot Selection - Decoration - HTML Compile
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="slot_selection" className="flex items-center gap-2">
            <CheckSquare className="h-4 w-4" />
            Slot Selection
          </TabsTrigger>
          <TabsTrigger value="decoration" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Decoration
          </TabsTrigger>
          <TabsTrigger value="html_compile" className="flex items-center gap-2">
            <Code className="h-4 w-4" />
            HTML Compile
          </TabsTrigger>
        </TabsList>

        {/* Slot Selection Tab */}
        <TabsContent value="slot_selection" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    slotSelectionState.isRunning ? "bg-purple-500 text-white" : "bg-purple-100 text-purple-600"
                  }`}>
                    {slotSelectionState.isRunning ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <CheckSquare className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <CardTitle className="text-lg">Signal Slot Selection</CardTitle>
                    <CardDescription>
                      Select stories for Signal: 1 top story, 3 feature stories, 5 quick signals
                    </CardDescription>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchSlotData(true)}
                  disabled={isLoadingSlots}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${isLoadingSlots ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {slotSelectionState.isRunning ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary" className="bg-purple-100 text-purple-700 hover:bg-purple-100">
                      {slotSelectionState.jobStatus === "queued" ? "Queued" : "Running"}
                    </Badge>
                    <div className="flex items-center gap-1.5 text-purple-600">
                      <Timer className="h-3.5 w-3.5" />
                      <span className="font-mono text-sm font-medium">
                        {formatTime(slotSelectionState.elapsedTime)}
                      </span>
                    </div>
                  </div>
                  <Progress value={undefined} className="h-1.5" />
                  <div className="flex items-center justify-between">
                    <code className="text-[10px] text-zinc-400">{slotSelectionState.jobId?.slice(0, 8)}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => cancelJob("slot_selection")}
                      disabled={isCancelling}
                      className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Stop
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {slotSelectionState.result && (
                    <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-lg px-3 py-2">
                      <CheckCircle className="h-4 w-4 flex-shrink-0" />
                      <span>Slot selection completed successfully</span>
                    </div>
                  )}
                  <Button
                    onClick={() => runJob("slot_selection")}
                    disabled={anyJobRunning}
                    className="w-full bg-purple-500 hover:bg-purple-600 text-white"
                  >
                    <CheckSquare className="h-4 w-4 mr-2" />
                    Run Slot Selection
                  </Button>
                </div>
              )}

              {/* Current Slot Data Display */}
              {slotData && (
                <div className="mt-6 pt-6 border-t">
                  <h4 className="text-sm font-medium text-zinc-700 mb-3 flex items-center gap-2">
                    Current Issue: #{slotData.issue_number || "N/A"}
                    <Badge variant="outline" className="text-xs">
                      {slotData.status || "unknown"}
                    </Badge>
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.entries(SLOT_LABELS).map(([key, label]) => {
                      const value = slotData[key];
                      const hasValue = !!value;
                      return (
                        <div
                          key={key}
                          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
                            hasValue ? "bg-zinc-50" : "bg-zinc-50/50"
                          }`}
                        >
                          {hasValue ? (
                            <CheckCircle className="h-4 w-4 text-emerald-500 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-zinc-300 flex-shrink-0" />
                          )}
                          <span className={hasValue ? "text-zinc-700" : "text-zinc-400"}>
                            {label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Decoration Tab */}
        <TabsContent value="decoration" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                    decorationState.isRunning ? "bg-blue-500 text-white" : "bg-blue-100 text-blue-600"
                  }`}>
                    {decorationState.isRunning ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : (
                      <Sparkles className="h-5 w-5" />
                    )}
                  </div>
                  <div>
                    <CardTitle className="text-lg">Signal Decoration</CardTitle>
                    <CardDescription>
                      Generate AI headlines, deks, and signal summaries (no images)
                    </CardDescription>
                  </div>
                </div>
                {slotData?.id && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchDecorationData(slotData.id, true)}
                    disabled={isLoadingDecorations}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${isLoadingDecorations ? "animate-spin" : ""}`} />
                    Refresh
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {decorationState.isRunning ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                      {decorationState.jobStatus === "queued" ? "Queued" : "Running"}
                    </Badge>
                    <div className="flex items-center gap-1.5 text-blue-600">
                      <Timer className="h-3.5 w-3.5" />
                      <span className="font-mono text-sm font-medium">
                        {formatTime(decorationState.elapsedTime)}
                      </span>
                    </div>
                  </div>
                  <Progress value={undefined} className="h-1.5" />
                  <div className="flex items-center justify-between">
                    <code className="text-[10px] text-zinc-400">{decorationState.jobId?.slice(0, 8)}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => cancelJob("decoration")}
                      disabled={isCancelling}
                      className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Stop
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {decorationState.result && (
                    <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-lg px-3 py-2">
                      <CheckCircle className="h-4 w-4 flex-shrink-0" />
                      <span>Decoration completed successfully</span>
                    </div>
                  )}
                  <Button
                    onClick={() => runJob("decoration")}
                    disabled={anyJobRunning}
                    className="w-full bg-blue-500 hover:bg-blue-600 text-white"
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    Run Decoration
                  </Button>
                </div>
              )}

              {/* Decoration Data Display */}
              {decorationData.length > 0 && (
                <div className="mt-6 pt-6 border-t">
                  <h4 className="text-sm font-medium text-zinc-700 mb-3">
                    Decorated Stories ({decorationData.length})
                  </h4>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {decorationData.map((decoration) => (
                      <div
                        key={decoration.id}
                        className="flex items-start gap-3 px-3 py-2 rounded-lg bg-zinc-50 text-sm"
                      >
                        <Badge variant="outline" className="text-xs flex-shrink-0">
                          {decoration.section}
                        </Badge>
                        <div className="flex-1 min-w-0">
                          <p className="text-zinc-700 truncate">
                            {decoration.ai_headline || decoration.signal_summary || "No headline"}
                          </p>
                          {decoration.ai_dek && (
                            <p className="text-zinc-500 text-xs truncate mt-0.5">
                              {decoration.ai_dek}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* HTML Compile Tab */}
        <TabsContent value="html_compile" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                  htmlCompileState.isRunning ? "bg-emerald-500 text-white" : "bg-emerald-100 text-emerald-600"
                }`}>
                  {htmlCompileState.isRunning ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Code className="h-5 w-5" />
                  )}
                </div>
                <div>
                  <CardTitle className="text-lg">Signal HTML Compile</CardTitle>
                  <CardDescription>
                    Compile the Signal newsletter into HTML (text-only format)
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {htmlCompileState.isRunning ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                      {htmlCompileState.jobStatus === "queued" ? "Queued" : "Running"}
                    </Badge>
                    <div className="flex items-center gap-1.5 text-emerald-600">
                      <Timer className="h-3.5 w-3.5" />
                      <span className="font-mono text-sm font-medium">
                        {formatTime(htmlCompileState.elapsedTime)}
                      </span>
                    </div>
                  </div>
                  <Progress value={undefined} className="h-1.5" />
                  <div className="flex items-center justify-between">
                    <code className="text-[10px] text-zinc-400">{htmlCompileState.jobId?.slice(0, 8)}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => cancelJob("html_compile")}
                      disabled={isCancelling}
                      className="h-7 px-2 text-xs text-zinc-500 hover:text-red-600"
                    >
                      <Square className="h-3 w-3 mr-1" />
                      Stop
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {htmlCompileState.result && (
                    <div className="flex items-center gap-2 text-sm text-emerald-600 bg-emerald-50 rounded-lg px-3 py-2">
                      <CheckCircle className="h-4 w-4 flex-shrink-0" />
                      <span>HTML compile completed successfully</span>
                    </div>
                  )}
                  <Button
                    onClick={() => runJob("html_compile")}
                    disabled={anyJobRunning}
                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-white"
                  >
                    <Code className="h-4 w-4 mr-2" />
                    Run HTML Compile
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Info Card */}
      <Card className="bg-zinc-50 border-zinc-200">
        <CardContent className="py-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-zinc-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-zinc-600">
              <p className="font-medium text-zinc-700 mb-2">Signal Newsletter Pipeline</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="flex items-start gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded bg-purple-100 text-purple-600 text-[10px] font-bold flex-shrink-0">1</span>
                  <span><strong>Slot Selection</strong> - Select 9 stories: 1 top, 3 features, 5 signals</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded bg-blue-100 text-blue-600 text-[10px] font-bold flex-shrink-0">2</span>
                  <span><strong>Decoration</strong> - Generate headlines, deks, and summaries</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded bg-emerald-100 text-emerald-600 text-[10px] font-bold flex-shrink-0">3</span>
                  <span><strong>HTML Compile</strong> - Build text-only email HTML</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
