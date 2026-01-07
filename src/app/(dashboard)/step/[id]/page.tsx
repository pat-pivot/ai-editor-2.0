"use client";

import { notFound } from "next/navigation";
import { use, useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { getStepConfig } from "@/lib/step-config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { LiveExecutionLogs } from "@/components/step/live-execution-logs";
import { SystemPrompts } from "@/components/step/system-prompts";
import { StepData } from "@/components/step/step-data";
import { Progress } from "@/components/ui/progress";
import { ZeroinIngestPanel } from "@/components/step/zeroin-ingest-panel";
import { HtmlPreview } from "@/components/step/html-preview";
import { ScheduleModal, SchedulingStatusBanner } from "@/components/step/schedule-modal";
import { formatDateET, formatDuration } from "@/lib/date-utils";

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

// Step 3 has two jobs: decoration and images
const STEP_3_JOBS = {
  decoration: { name: "Run Decoration", icon: "edit_note" },
  images: { name: "Generate Images", icon: "image" },
};

// Step 4 has three jobs: compile, mautic send, gmail send
const STEP_4_JOBS = {
  html_compile: { name: "Compile HTML", icon: "code" },
  mautic_send: { name: "Send via Mautic", icon: "send" },
  gmail_send: { name: "Test via Gmail", icon: "mail" },
};

// Step 1 slot definitions
const PREFILTER_SLOTS = [1, 2, 3, 4, 5];

interface SlotState {
  isRunning: boolean;
  jobId: string | null;
  jobStatus: "queued" | "started" | "finished" | "failed" | null;
  elapsedTime: number;
  result: { written: number; elapsed: number } | null;
}

export default function StepPage({ params }: PageProps) {
  const { id } = use(params);
  const stepId = parseInt(id, 10);
  const [isRunning, setIsRunning] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showCompletion, setShowCompletion] = useState(false);
  const [lastResult, setLastResult] = useState<{ processed: number; elapsed: number } | null>(null);
  // Step 4 defaults to "preview" tab, others to "logs"
  const [activeTab, setActiveTab] = useState(() => stepId === 4 ? "preview" : "logs");

  // Step 0 specific: Track AI Scoring job separately
  const [isAiScoringRunning, setIsAiScoringRunning] = useState(false);
  const [aiScoringJobId, setAiScoringJobId] = useState<string | null>(null);
  const [aiScoringJobStatus, setAiScoringJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [aiScoringElapsedTime, setAiScoringElapsedTime] = useState(0);
  const [currentJobType, setCurrentJobType] = useState<"ingest" | "ai_scoring" | "decoration" | "images" | "html_compile" | "mautic_send" | "gmail_send" | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // Step 3 specific: Track Image Generation job separately
  const [isImageGenRunning, setIsImageGenRunning] = useState(false);
  const [imageGenJobId, setImageGenJobId] = useState<string | null>(null);
  const [imageGenJobStatus, setImageGenJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [imageGenElapsedTime, setImageGenElapsedTime] = useState(0);

  // Step 4 specific: Track Mautic Send job separately
  const [isMauticSendRunning, setIsMauticSendRunning] = useState(false);
  const [mauticSendJobId, setMauticSendJobId] = useState<string | null>(null);
  const [mauticSendJobStatus, setMauticSendJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [mauticSendElapsedTime, setMauticSendElapsedTime] = useState(0);

  // Step 4 specific: Track Gmail Send job separately
  const [isGmailSendRunning, setIsGmailSendRunning] = useState(false);
  const [gmailSendJobId, setGmailSendJobId] = useState<string | null>(null);
  const [gmailSendJobStatus, setGmailSendJobStatus] = useState<"queued" | "started" | "finished" | "failed" | null>(null);
  const [gmailSendElapsedTime, setGmailSendElapsedTime] = useState(0);

  // Step 4 specific: Schedule modal, newsletter preview data, Gmail recipient
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [isScheduling, setIsScheduling] = useState(false);
  const [isCancellingSchedule, setIsCancellingSchedule] = useState(false);
  const [gmailRecipient, setGmailRecipient] = useState("patsimmons21@gmail.com");
  interface NewsletterPreviewData {
    html: string;
    subject_line: string;
    summary: string;
    issue_id: string;
    send_date: string;
    status: string;
    scheduled_send_time?: string;
    scheduled_at?: string;
    record_id: string;
  }
  const [newsletterData, setNewsletterData] = useState<NewsletterPreviewData | null>(null);

  // Step 1 specific: Track individual slot jobs
  const [slotStates, setSlotStates] = useState<Record<number, SlotState>>({
    1: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    2: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    3: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    4: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
    5: { isRunning: false, jobId: null, jobStatus: null, elapsedTime: 0, result: null },
  });
  const [cancellingSlot, setCancellingSlot] = useState<number | null>(null);

  // Last run tracking
  interface StepLastRunInfo {
    timestamp: string;
    duration_seconds: number;
    status: "success" | "failed" | "running";
  }
  const [stepLastRun, setStepLastRun] = useState<StepLastRunInfo | null>(null);

  // Fetch last run data on mount
  useEffect(() => {
    const fetchLastRun = async () => {
      try {
        const response = await fetch(`/api/jobs/last-run?step_id=${stepId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.last_run) {
            setStepLastRun(data.last_run);
          }
        }
      } catch (error) {
        console.error("Error fetching last run data:", error);
      }
    };

    fetchLastRun();
  }, [stepId]);

  // Update a specific slot's state
  const updateSlotState = (slotNum: number, updates: Partial<SlotState>) => {
    setSlotStates(prev => ({
      ...prev,
      [slotNum]: { ...prev[slotNum], ...updates },
    }));
  };

  // Check if any slot is running
  const anySlotRunning = Object.values(slotStates).some(s => s.isRunning);

  // Cancel a slot job
  const cancelSlotJob = async (slotNum: number) => {
    const slotJobId = slotStates[slotNum].jobId;
    if (!slotJobId) return;

    setCancellingSlot(slotNum);
    try {
      const response = await fetch("/api/jobs/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jobId: slotJobId }),
      });

      const data = await response.json();
      if (response.ok) {
        toast.success(`Slot ${slotNum} cancelled`);
        updateSlotState(slotNum, { isRunning: false, jobId: null, jobStatus: null });
      } else {
        toast.error(data.error || "Failed to cancel");
      }
    } catch (error) {
      console.error("Error cancelling slot job:", error);
      toast.error("Failed to cancel");
    } finally {
      setCancellingSlot(null);
    }
  };

  // Run a single slot
  const runSlot = async (slotNum: number) => {
    updateSlotState(slotNum, { isRunning: true, elapsedTime: 0, result: null });

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: `prefilter_slot_${slotNum}` }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        updateSlotState(slotNum, { jobId: data.job_id, jobStatus: "queued" });
        toast.success(`Slot ${slotNum} Started`);
      } else {
        updateSlotState(slotNum, { isRunning: false });
        throw new Error(data.error || "Failed to start");
      }
    } catch (error) {
      updateSlotState(slotNum, { isRunning: false });
      toast.error(error instanceof Error ? error.message : "Failed to start");
    }
  };

  // Cancel running job
  const cancelJob = async () => {
    const currentJobId = currentJobType === "ai_scoring" ? aiScoringJobId
      : currentJobType === "images" ? imageGenJobId
      : currentJobType === "mautic_send" ? mauticSendJobId
      : currentJobType === "gmail_send" ? gmailSendJobId
      : jobId;
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
        } else if (currentJobType === "images") {
          setIsImageGenRunning(false);
          setImageGenJobId(null);
          setImageGenJobStatus(null);
        } else if (currentJobType === "mautic_send") {
          setIsMauticSendRunning(false);
          setMauticSendJobId(null);
          setMauticSendJobStatus(null);
        } else if (currentJobType === "gmail_send") {
          setIsGmailSendRunning(false);
          setGmailSendJobId(null);
          setGmailSendJobStatus(null);
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

  // Step 4: Handle scheduling newsletter
  const handleSchedule = async (scheduledTime: Date) => {
    if (!newsletterData) {
      toast.error("No newsletter data available");
      return;
    }

    setIsScheduling(true);
    try {
      const response = await fetch("/api/newsletter/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          issue_id: newsletterData.issue_id,
          record_id: newsletterData.record_id,
          scheduled_time: scheduledTime.toISOString(),
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast.success("Newsletter Scheduled", {
          description: data.message,
        });
        // Update local state to reflect scheduled status
        setNewsletterData({
          ...newsletterData,
          status: "scheduled",
          scheduled_send_time: scheduledTime.toISOString(),
          scheduled_at: new Date().toISOString(),
        });
      } else {
        throw new Error(data.error || "Failed to schedule newsletter");
      }
    } catch (error) {
      console.error("Error scheduling newsletter:", error);
      toast.error("Scheduling Failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
      throw error; // Re-throw so modal knows to stay open
    } finally {
      setIsScheduling(false);
    }
  };

  // Step 4: Handle cancelling scheduled newsletter
  const handleCancelSchedule = async () => {
    if (!newsletterData) return;

    setIsCancellingSchedule(true);
    try {
      const response = await fetch("/api/newsletter/schedule", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          record_id: newsletterData.record_id,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast.success("Schedule Cancelled", {
          description: "Newsletter scheduling has been cancelled",
        });
        // Update local state
        setNewsletterData({
          ...newsletterData,
          status: "next-send",
          scheduled_send_time: undefined,
          scheduled_at: undefined,
        });
      } else {
        throw new Error(data.error || "Failed to cancel schedule");
      }
    } catch (error) {
      console.error("Error cancelling schedule:", error);
      toast.error("Cancellation Failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsCancellingSchedule(false);
    }
  };

  // Step 4: Handle Gmail send with recipient
  const handleGmailSend = async () => {
    if (!gmailRecipient || !gmailRecipient.includes("@")) {
      toast.error("Invalid email address");
      return;
    }

    setIsGmailSendRunning(true);
    setGmailSendElapsedTime(0);
    setCurrentJobType("gmail_send");
    setShowCompletion(false);

    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          step: "gmail_send",
          params: { recipient: gmailRecipient },
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setGmailSendJobId(data.job_id);
        setGmailSendJobStatus("queued");
        toast.success("Test Email Started", {
          description: `Sending test email to ${gmailRecipient}`,
        });
      } else {
        setIsGmailSendRunning(false);
        throw new Error(data.error || "Failed to start Gmail send");
      }
    } catch (error) {
      setIsGmailSendRunning(false);
      toast.error("Error", {
        description: error instanceof Error ? error.message : "Failed to start Gmail send",
      });
    }
  };

  if (isNaN(stepId) || stepId < 0 || stepId > 5) {
    notFound();
  }

  const stepConfig = getStepConfig(stepId);

  if (!stepConfig) {
    notFound();
  }

  const handleRunNow = async (jobType?: "ingest" | "ai_scoring" | "decoration" | "images" | "html_compile" | "mautic_send" | "gmail_send") => {
    // For Step 0, Step 3, and Step 4, use the specified jobType; otherwise use the step's job name
    const jobName = (stepId === 0 || stepId === 3 || stepId === 4) && jobType ? jobType : STEP_JOB_NAMES[stepId];
    if (!jobName) return;

    const jobDisplayName = stepId === 0 && jobType
      ? STEP_0_JOBS[jobType as "ingest" | "ai_scoring"].name
      : stepId === 3 && jobType
      ? STEP_3_JOBS[jobType as "decoration" | "images"].name
      : stepId === 4 && jobType
      ? STEP_4_JOBS[jobType as "html_compile" | "mautic_send" | "gmail_send"].name
      : stepConfig.name;

    // For Step 0 AI Scoring, use separate state
    if (stepId === 0 && jobType === "ai_scoring") {
      setIsAiScoringRunning(true);
      setAiScoringElapsedTime(0);
      setCurrentJobType("ai_scoring");
    } else if (stepId === 3 && jobType === "images") {
      // For Step 3 Image Generation, use separate state
      setIsImageGenRunning(true);
      setImageGenElapsedTime(0);
      setCurrentJobType("images");
    } else if (stepId === 4 && jobType === "mautic_send") {
      // For Step 4 Mautic Send, use separate state
      setIsMauticSendRunning(true);
      setMauticSendElapsedTime(0);
      setCurrentJobType("mautic_send");
    } else if (stepId === 4 && jobType === "gmail_send") {
      // For Step 4 Gmail Send, use separate state
      setIsGmailSendRunning(true);
      setGmailSendElapsedTime(0);
      setCurrentJobType("gmail_send");
    } else {
      setIsRunning(true);
      setElapsedTime(0);
      setCurrentJobType(stepId === 0 ? "ingest" : stepId === 3 ? "decoration" : stepId === 4 ? "html_compile" : null);
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
        } else if (stepId === 3 && jobType === "images") {
          setImageGenJobId(data.job_id);
          setImageGenJobStatus("queued");
        } else if (stepId === 4 && jobType === "mautic_send") {
          setMauticSendJobId(data.job_id);
          setMauticSendJobStatus("queued");
        } else if (stepId === 4 && jobType === "gmail_send") {
          setGmailSendJobId(data.job_id);
          setGmailSendJobStatus("queued");
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
        } else if (stepId === 3 && jobType === "images") {
          setIsImageGenRunning(false);
        } else if (stepId === 4 && jobType === "mautic_send") {
          setIsMauticSendRunning(false);
        } else if (stepId === 4 && jobType === "gmail_send") {
          setIsGmailSendRunning(false);
        } else {
          setIsRunning(false);
        }
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      if (stepId === 0 && jobType === "ai_scoring") {
        setIsAiScoringRunning(false);
      } else if (stepId === 3 && jobType === "images") {
        setIsImageGenRunning(false);
      } else if (stepId === 4 && jobType === "mautic_send") {
        setIsMauticSendRunning(false);
      } else if (stepId === 4 && jobType === "gmail_send") {
        setIsGmailSendRunning(false);
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

  // Poll Image Generation job status (Step 3 only)
  useEffect(() => {
    if (!imageGenJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setImageGenElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${imageGenJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setImageGenJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsImageGenRunning(false);
          setImageGenJobId(null);
          setImageGenJobStatus(status.status);
          setCurrentJobType(null);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const generatedCount = status.result?.generated || 0;
            const failedCount = status.result?.failed || 0;
            setLastResult({ processed: generatedCount, elapsed: finalElapsed });
            setShowCompletion(true);
            toast.success("Image Generation Completed", {
              description: `Generated ${generatedCount} images${failedCount > 0 ? `, ${failedCount} failed` : ""} in ${finalElapsed}s`,
            });
            window.dispatchEvent(new CustomEvent("jobCompleted", { detail: { stepId } }));
          } else {
            toast.error("Image Generation Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling Image Generation job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [imageGenJobId, stepId]);

  // Poll Mautic Send job status (Step 4 only)
  useEffect(() => {
    if (!mauticSendJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setMauticSendElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${mauticSendJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setMauticSendJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsMauticSendRunning(false);
          setMauticSendJobId(null);
          setMauticSendJobStatus(status.status);
          setCurrentJobType(null);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const sentCount = status.result?.sent_count || 0;
            const failedCount = status.result?.failed_recipients || 0;
            setLastResult({ processed: sentCount, elapsed: finalElapsed });
            setShowCompletion(true);
            toast.success("Mautic Send Completed", {
              description: `Sent to ${sentCount} recipients${failedCount > 0 ? `, ${failedCount} failed` : ""} in ${finalElapsed}s`,
            });
            window.dispatchEvent(new CustomEvent("jobCompleted", { detail: { stepId } }));
          } else {
            toast.error("Mautic Send Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling Mautic Send job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [mauticSendJobId, stepId]);

  // Poll Gmail Send job status (Step 4 only)
  useEffect(() => {
    if (!gmailSendJobId) return;

    const startTime = Date.now();

    const timerInterval = setInterval(() => {
      setGmailSendElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/jobs/${gmailSendJobId}`);
        const status = await response.json();

        if (status.status === "started" || status.status === "queued") {
          setGmailSendJobStatus(status.status);
        }

        if (status.status === "finished" || status.status === "failed") {
          clearInterval(pollInterval);
          clearInterval(timerInterval);
          setIsGmailSendRunning(false);
          setGmailSendJobId(null);
          setGmailSendJobStatus(status.status);
          setCurrentJobType(null);

          const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

          if (status.status === "finished") {
            const recipientCount = status.result?.recipients?.length || 0;
            setLastResult({ processed: recipientCount, elapsed: finalElapsed });
            setShowCompletion(true);
            toast.success("Gmail Test Send Completed", {
              description: `Sent test email to ${recipientCount} recipient(s) in ${finalElapsed}s`,
            });
            window.dispatchEvent(new CustomEvent("jobCompleted", { detail: { stepId } }));
          } else {
            toast.error("Gmail Test Send Failed", {
              description: status.error || "Unknown error occurred",
            });
          }
        }
      } catch (error) {
        console.error("Error polling Gmail Send job status:", error);
      }
    }, 2000);

    return () => {
      clearInterval(pollInterval);
      clearInterval(timerInterval);
    };
  }, [gmailSendJobId, stepId]);

  // Poll slot job status (Step 1 only)
  useEffect(() => {
    if (stepId !== 1) return;

    const intervals: Record<number, { poll: NodeJS.Timeout; timer: NodeJS.Timeout }> = {};

    PREFILTER_SLOTS.forEach(slotNum => {
      const state = slotStates[slotNum];
      if (!state.jobId) return;

      const startTime = Date.now();

      intervals[slotNum] = {
        timer: setInterval(() => {
          updateSlotState(slotNum, { elapsedTime: Math.floor((Date.now() - startTime) / 1000) });
        }, 1000),
        poll: setInterval(async () => {
          try {
            const response = await fetch(`/api/jobs/${state.jobId}`);
            const status = await response.json();

            if (status.status === "started" || status.status === "queued") {
              updateSlotState(slotNum, { jobStatus: status.status });
            }

            if (status.status === "finished" || status.status === "failed") {
              clearInterval(intervals[slotNum].poll);
              clearInterval(intervals[slotNum].timer);

              const finalElapsed = Math.floor((Date.now() - startTime) / 1000);

              if (status.status === "finished") {
                const writtenCount = status.result?.written || 0;
                updateSlotState(slotNum, {
                  isRunning: false,
                  jobId: null,
                  jobStatus: "finished",
                  result: { written: writtenCount, elapsed: finalElapsed },
                });
                toast.success(`Slot ${slotNum} Completed`, {
                  description: `Wrote ${writtenCount} records in ${finalElapsed}s`,
                });
              } else {
                updateSlotState(slotNum, {
                  isRunning: false,
                  jobId: null,
                  jobStatus: "failed",
                });
                toast.error(`Slot ${slotNum} Failed`, {
                  description: status.error || "Unknown error",
                });
              }
            }
          } catch (error) {
            console.error(`Error polling slot ${slotNum}:`, error);
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
  }, [stepId, slotStates[1].jobId, slotStates[2].jobId, slotStates[3].jobId, slotStates[4].jobId, slotStates[5].jobId]);

  // Next run calculation - only for step 1 which has scheduled automation
  const getNextRunDisplay = () => {
    // Step 1 Pre-Filter runs every 4 hours: 6 AM, 10 AM, 2 PM, 6 PM, 10 PM ET
    const schedule = "0 6,10,14,18,22 * * *";
    const parts = schedule.split(" ");
    const hours = parts[1].split(",").map(h => parseInt(h));

    const now = new Date();
    const etNow = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
    const currentHour = etNow.getHours();

    // Find next scheduled hour
    for (const hour of hours) {
      if (hour > currentHour) {
        const nextRun = new Date(etNow);
        nextRun.setHours(hour, 0, 0, 0);
        return formatDateET(nextRun).replace(/:00 /, " ").replace(/:00 /, " ");
      }
    }

    // All today's hours passed, use first hour tomorrow
    const nextRun = new Date(etNow);
    nextRun.setDate(nextRun.getDate() + 1);
    nextRun.setHours(hours[0], 0, 0, 0);
    return formatDateET(nextRun).replace(/:00 /, " ").replace(/:00 /, " ");
  };

  // Step 0 uses the new Zeroin Ingest panel
  if (stepId === 0) {
    return (
      <div className="p-6">
        <ZeroinIngestPanel />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Step Header */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              {/* Only show icon for step 1 (Pre-Filter) which has scheduled automation */}
              {stepId === 1 && (
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <MaterialIcon name={stepConfig.icon} className="text-2xl" />
                </div>
              )}
              <div>
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">
                    Step {stepConfig.id}: {stepConfig.name}
                  </CardTitle>
                  {/* Only show schedule badge for step 1 */}
                  {stepId === 1 && (
                    <Badge variant="secondary" className="font-mono text-xs">
                      {stepConfig.schedule.split(" ")[0]} {stepConfig.schedule.split(" ")[1]}
                    </Badge>
                  )}
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
            ) : stepId === 3 ? (
              /* Step 3: Two buttons for Decoration and Image Generation */
              <div className="flex gap-2">
                <Button
                  className="gap-2"
                  onClick={() => handleRunNow("decoration")}
                  disabled={isRunning || isImageGenRunning}
                >
                  <MaterialIcon
                    name={isRunning ? "sync" : "edit_note"}
                    className={`text-lg ${isRunning ? "animate-spin" : ""}`}
                  />
                  {isRunning ? `Decorating... ${elapsedTime}s` : "Run Decoration"}
                </Button>
                <Button
                  className="gap-2"
                  variant="secondary"
                  onClick={() => handleRunNow("images")}
                  disabled={isRunning || isImageGenRunning}
                >
                  <MaterialIcon
                    name={isImageGenRunning ? "sync" : "image"}
                    className={`text-lg ${isImageGenRunning ? "animate-spin" : ""}`}
                  />
                  {isImageGenRunning ? `Generating... ${imageGenElapsedTime}s` : "Generate Images"}
                </Button>
              </div>
            ) : stepId === 4 ? (
              /* Step 4: Compile, Schedule, and Gmail Test buttons */
              <div className="flex items-center gap-2">
                <Button
                  className="gap-2"
                  onClick={() => handleRunNow("html_compile")}
                  disabled={isRunning || isMauticSendRunning || isGmailSendRunning}
                >
                  <MaterialIcon
                    name={isRunning && currentJobType === "html_compile" ? "sync" : "code"}
                    className={`text-lg ${isRunning && currentJobType === "html_compile" ? "animate-spin" : ""}`}
                  />
                  {isRunning && currentJobType === "html_compile" ? `Compiling... ${elapsedTime}s` : "Compile HTML"}
                </Button>
                <Button
                  className="gap-2"
                  variant="secondary"
                  onClick={() => setScheduleModalOpen(true)}
                  disabled={isRunning || isMauticSendRunning || isGmailSendRunning || !newsletterData}
                >
                  <MaterialIcon name="schedule" className="text-lg" />
                  Schedule via Mautic
                </Button>
                <div className="flex items-center gap-1 border rounded-md pl-2">
                  <Input
                    type="email"
                    placeholder="Test email"
                    value={gmailRecipient}
                    onChange={(e) => setGmailRecipient(e.target.value)}
                    className="h-9 w-48 border-0 focus-visible:ring-0 text-sm"
                  />
                  <Button
                    className="gap-2 h-9"
                    variant="outline"
                    onClick={handleGmailSend}
                    disabled={isRunning || isMauticSendRunning || isGmailSendRunning || !newsletterData}
                  >
                    <MaterialIcon
                      name={isGmailSendRunning ? "sync" : "mail"}
                      className={`text-lg ${isGmailSendRunning ? "animate-spin" : ""}`}
                    />
                    {isGmailSendRunning ? `${gmailSendElapsedTime}s` : "Test"}
                  </Button>
                </div>
              </div>
            ) : stepId === 1 ? (
              /* Step 1: No single run button - slot cards shown below */
              null
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
            {stepLastRun ? (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Last Run:</span>
                <span className="font-medium">{formatDateET(stepLastRun.timestamp)}</span>
                <span className="text-muted-foreground">|</span>
                <span className="font-mono text-muted-foreground">{formatDuration(stepLastRun.duration_seconds)}</span>
                <span className="text-muted-foreground">|</span>
                <StatusBadge status={stepLastRun.status === "failed" ? "error" : stepLastRun.status} />
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Last Run:</span>
                <span className="text-muted-foreground italic">No recent runs</span>
              </div>
            )}
            {/* Only show Next Run for steps with automation (step 1 Pre-Filter) */}
            {stepId === 1 && (
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Next Run:</span>
                <span className="font-medium">{getNextRunDisplay()}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Step 4: Scheduling Status Banner */}
      {stepId === 4 && newsletterData?.status === "scheduled" && newsletterData.scheduled_send_time && (
        <SchedulingStatusBanner
          scheduledTime={newsletterData.scheduled_send_time}
          onCancel={handleCancelSchedule}
          isCancelling={isCancellingSchedule}
        />
      )}

      {/* Tabs Section - Directly after header */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-zinc-100">
          {/* Step 4: Preview tab first */}
          {stepId === 4 && (
            <TabsTrigger value="preview" className="data-[state=active]:bg-white">
              Email Preview
            </TabsTrigger>
          )}
          <TabsTrigger value="logs" className="data-[state=active]:bg-white">
            Execution Logs
          </TabsTrigger>
          {stepConfig.prompts.length > 0 && (
            <TabsTrigger value="prompts" className="data-[state=active]:bg-white">
              System Prompts
            </TabsTrigger>
          )}
          {stepConfig.dataTable && (
            <TabsTrigger value="data" className="data-[state=active]:bg-white">
              {stepConfig.dataTable.name}
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="logs" className="space-y-4">
          {/* Step 1: Slot Pre-Filter Cards */}
          {stepId === 1 && (
            <div className="grid grid-cols-5 gap-3">
              {PREFILTER_SLOTS.map(slotNum => {
                const state = slotStates[slotNum];
                return (
                  <Card key={slotNum} className={state.isRunning ? "border-orange-300 bg-orange-50/30" : ""}>
                    <CardContent className="p-4">
                      <div className="text-center mb-3">
                        <span className="font-semibold text-sm">
                          Slot {slotNum} Pre-Filter Agent
                        </span>
                      </div>

                      {state.isRunning ? (
                        <div className="space-y-2">
                          <div className="flex items-center justify-center gap-2">
                            <Badge variant="outline" className="bg-orange-100 text-orange-700 border-orange-200 text-xs">
                              {state.jobStatus === "queued" ? "Queued" : "Running"}
                            </Badge>
                            <span className="font-mono text-sm font-bold text-orange-700">
                              {Math.floor(state.elapsedTime / 60)}:{String(state.elapsedTime % 60).padStart(2, "0")}
                            </span>
                          </div>
                          <Progress value={undefined} className="h-1.5 bg-orange-100" />
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => cancelSlotJob(slotNum)}
                            disabled={cancellingSlot === slotNum}
                            className="w-full h-8 text-xs"
                          >
                            {cancellingSlot === slotNum ? "Stopping..." : "Stop"}
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {state.result && (
                            <div className="text-xs text-center text-emerald-600 bg-emerald-50 rounded px-2 py-1">
                              {state.result.written} records • {state.result.elapsed}s
                            </div>
                          )}
                          {state.jobStatus === "failed" && (
                            <div className="text-xs text-center text-red-600 bg-red-50 rounded px-2 py-1">
                              Failed
                            </div>
                          )}
                          <Button
                            onClick={() => runSlot(slotNum)}
                            disabled={anySlotRunning}
                            className="w-full h-8 text-xs bg-orange-500 hover:bg-orange-600 text-white"
                          >
                            Run Slot {slotNum}
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}

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
          {(isRunning || isAiScoringRunning || isMauticSendRunning || isGmailSendRunning) && (
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
                            : currentJobType === "html_compile"
                            ? (jobStatus === "queued" ? "Compile Queued" : "Compiling HTML")
                            : currentJobType === "mautic_send"
                            ? (mauticSendJobStatus === "queued" ? "Mautic Send Queued" : "Sending via Mautic")
                            : currentJobType === "gmail_send"
                            ? (gmailSendJobStatus === "queued" ? "Gmail Send Queued" : "Sending Test via Gmail")
                            : (jobStatus === "queued" ? "Job Queued" : "Job Running")}
                        </span>
                        <Badge variant="outline" className="bg-blue-100 text-blue-700 border-blue-200">
                          {(currentJobType === "ai_scoring" ? aiScoringJobStatus
                            : currentJobType === "mautic_send" ? mauticSendJobStatus
                            : currentJobType === "gmail_send" ? gmailSendJobStatus
                            : jobStatus) === "queued"
                            ? "Waiting for worker..."
                            : "Processing..."}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-lg font-bold text-blue-700">
                          {Math.floor((currentJobType === "ai_scoring" ? aiScoringElapsedTime
                            : currentJobType === "mautic_send" ? mauticSendElapsedTime
                            : currentJobType === "gmail_send" ? gmailSendElapsedTime
                            : elapsedTime) / 60)}:
                          {String((currentJobType === "ai_scoring" ? aiScoringElapsedTime
                            : currentJobType === "mautic_send" ? mauticSendElapsedTime
                            : currentJobType === "gmail_send" ? gmailSendElapsedTime
                            : elapsedTime) % 60).padStart(2, "0")}
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
                      <span>Job ID: {(currentJobType === "ai_scoring" ? aiScoringJobId
                        : currentJobType === "mautic_send" ? mauticSendJobId
                        : currentJobType === "gmail_send" ? gmailSendJobId
                        : jobId)?.slice(0, 8)}...</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Execution Logs */}
          <LiveExecutionLogs stepId={stepId} title={`Step ${stepId}: ${stepConfig.name} Logs`} />
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

        {/* Step 4: Email Preview Tab */}
        {stepId === 4 && (
          <TabsContent value="preview">
            <HtmlPreview onPreviewLoad={setNewsletterData} />
          </TabsContent>
        )}
      </Tabs>

      {/* Step 4: Schedule Modal */}
      {stepId === 4 && newsletterData && (
        <ScheduleModal
          open={scheduleModalOpen}
          onOpenChange={setScheduleModalOpen}
          issueId={newsletterData.issue_id}
          onSchedule={handleSchedule}
          isScheduling={isScheduling}
        />
      )}
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
