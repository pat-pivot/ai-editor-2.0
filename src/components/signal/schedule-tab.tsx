"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Send,
  RefreshCw,
  CheckCircle,
  Loader2,
  AlertCircle,
  Clock,
  Mail,
  Calendar,
} from "lucide-react";

interface SignalIssue {
  recordId: string;
  issueId: string;
  issueDate: string;
  subjectLine: string;
  status: string;
  compiledHtml: string | null;
  sentAt: string | null;
}

interface ScheduleResponse {
  success: boolean;
  issueId: string;
  issueRecordId: string;
  emailMessageId: number;
  campaignId: number;
  campaignStatus: string;
  scheduledFor: string;
  sentAt: string;
  message: string;
}

/**
 * Get default schedule time (tomorrow 5am ET)
 */
function getDefaultScheduleTime(): string {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Set to 5am ET (approximated as local time for the input)
  // The API will handle proper timezone conversion
  tomorrow.setHours(5, 0, 0, 0);

  // Format as datetime-local input value (YYYY-MM-DDTHH:MM)
  const year = tomorrow.getFullYear();
  const month = String(tomorrow.getMonth() + 1).padStart(2, "0");
  const day = String(tomorrow.getDate()).padStart(2, "0");
  const hours = String(tomorrow.getHours()).padStart(2, "0");
  const minutes = String(tomorrow.getMinutes()).padStart(2, "0");

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function ScheduleTab() {
  const [issues, setIssues] = useState<SignalIssue[]>([]);
  const [selectedIssue, setSelectedIssue] = useState<SignalIssue | null>(null);
  const [scheduleTime, setScheduleTime] = useState(getDefaultScheduleTime());
  const [isLoadingIssues, setIsLoadingIssues] = useState(false);
  const [isScheduling, setIsScheduling] = useState(false);
  const [lastResult, setLastResult] = useState<ScheduleResponse | null>(null);

  // Fetch compiled issues
  const fetchCompiledIssues = async (skipCache = false) => {
    setIsLoadingIssues(true);
    try {
      const url = `/api/signal/issues?status=compiled${skipCache ? "&skipCache=true" : ""}`;
      const response = await fetch(url);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to fetch issues");
      }

      setIssues(data.issues || []);

      // Auto-select the first issue if none selected
      if (data.issues?.length > 0 && !selectedIssue) {
        setSelectedIssue(data.issues[0]);
      }
    } catch (error) {
      console.error("Error fetching compiled issues:", error);
      toast.error("Failed to fetch issues", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsLoadingIssues(false);
    }
  };

  // Load issues on mount
  useEffect(() => {
    fetchCompiledIssues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle schedule submission
  const handleSchedule = async () => {
    if (!selectedIssue) {
      toast.error("No issue selected", {
        description: "Please select a compiled issue to schedule",
      });
      return;
    }

    setIsScheduling(true);
    setLastResult(null);

    try {
      const response = await fetch("/api/signal/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          issueRecordId: selectedIssue.recordId,
          scheduleTime: new Date(scheduleTime).toISOString(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to schedule newsletter");
      }

      setLastResult(data);
      toast.success("Newsletter Scheduled!", {
        description: data.message,
      });

      // Refresh issues list (the scheduled one should no longer appear)
      fetchCompiledIssues(true);
      setSelectedIssue(null);
    } catch (error) {
      console.error("Error scheduling newsletter:", error);
      toast.error("Scheduling Failed", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsScheduling(false);
    }
  };

  // Format date for display
  const formatDate = (dateStr: string) => {
    if (!dateStr) return "N/A";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100 text-orange-600">
              <Send className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">Send & Schedule</CardTitle>
              <CardDescription>
                Schedule compiled Signal newsletters to Ongage for delivery
              </CardDescription>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchCompiledIssues(true)}
            disabled={isLoadingIssues}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoadingIssues ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Success Result */}
        {lastResult && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-emerald-50 border border-emerald-200">
            <CheckCircle className="h-5 w-5 text-emerald-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-emerald-800">Newsletter Scheduled Successfully</p>
              <p className="text-emerald-700 mt-1">{lastResult.message}</p>
              <div className="mt-2 space-y-1 text-emerald-600 text-xs">
                <p>Campaign ID: {lastResult.campaignId}</p>
                <p>Email Message ID: {lastResult.emailMessageId}</p>
                <p>Status: {lastResult.campaignStatus}</p>
              </div>
            </div>
          </div>
        )}

        {/* No Compiled Issues Warning */}
        {!isLoadingIssues && issues.length === 0 && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200">
            <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-amber-800">No Compiled Issues</p>
              <p className="text-amber-700 mt-1">
                Run HTML Compile on an issue first, then return here to schedule it.
              </p>
            </div>
          </div>
        )}

        {/* Main Content Grid */}
        {issues.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column: Controls */}
            <div className="space-y-4">
              {/* Issue Selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-700 flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  Select Issue
                </label>
                <select
                  className="w-full h-10 px-3 rounded-md border border-zinc-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  value={selectedIssue?.recordId || ""}
                  onChange={(e) => {
                    const issue = issues.find((i) => i.recordId === e.target.value);
                    setSelectedIssue(issue || null);
                  }}
                >
                  <option value="">Select a compiled issue...</option>
                  {issues.map((issue) => (
                    <option key={issue.recordId} value={issue.recordId}>
                      {issue.issueId} - {issue.subjectLine || "No subject"}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selected Issue Details */}
              {selectedIssue && (
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-500">Issue ID</span>
                    <span className="text-sm text-zinc-700">{selectedIssue.issueId}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-500">Date</span>
                    <span className="text-sm text-zinc-700">{formatDate(selectedIssue.issueDate)}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-500">Status</span>
                    <Badge variant="secondary" className="bg-emerald-100 text-emerald-700">
                      {selectedIssue.status}
                    </Badge>
                  </div>
                  <div className="pt-2 border-t border-zinc-200">
                    <span className="text-xs font-medium text-zinc-500">Subject Line</span>
                    <p className="text-sm text-zinc-700 mt-1">{selectedIssue.subjectLine || "No subject line"}</p>
                  </div>
                </div>
              )}

              {/* Schedule Time Picker */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-700 flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Schedule Time (ET)
                </label>
                <input
                  type="datetime-local"
                  className="w-full h-10 px-3 rounded-md border border-zinc-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                />
                <p className="text-xs text-zinc-500 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Default: Tomorrow at 5:00 AM ET
                </p>
              </div>

              {/* Schedule Button */}
              <Button
                onClick={handleSchedule}
                disabled={!selectedIssue || isScheduling}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white"
              >
                {isScheduling ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Scheduling...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Schedule to Ongage
                  </>
                )}
              </Button>
            </div>

            {/* Right Column: HTML Preview */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-zinc-700">HTML Preview</label>
              <div className="border border-zinc-200 rounded-lg overflow-hidden bg-white">
                {selectedIssue?.compiledHtml ? (
                  <iframe
                    srcDoc={selectedIssue.compiledHtml}
                    className="w-full h-[500px] border-0"
                    title="Newsletter Preview"
                    sandbox="allow-same-origin"
                  />
                ) : (
                  <div className="h-[500px] flex items-center justify-center text-zinc-400 text-sm">
                    {selectedIssue ? "No HTML content available" : "Select an issue to preview"}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
