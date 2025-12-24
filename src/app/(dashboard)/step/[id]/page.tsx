"use client";

import { notFound } from "next/navigation";
import { use, useState } from "react";
import { toast } from "sonner";
import { getStepConfig } from "@/lib/step-config";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExecutionLogs } from "@/components/step/execution-logs";
import { SystemPrompts } from "@/components/step/system-prompts";
import { StepData } from "@/components/step/step-data";

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
  1: "prefilter",
  2: "slot_selection",
  3: "decoration",
  4: "html_compile",
  5: "mautic_send",
};

export default function StepPage({ params }: PageProps) {
  const { id } = use(params);
  const stepId = parseInt(id, 10);
  const [isRunning, setIsRunning] = useState(false);

  if (isNaN(stepId) || stepId < 1 || stepId > 5) {
    notFound();
  }

  const stepConfig = getStepConfig(stepId);

  if (!stepConfig) {
    notFound();
  }

  const handleRunNow = async () => {
    const jobName = STEP_JOB_NAMES[stepId];
    if (!jobName) return;

    setIsRunning(true);
    try {
      const response = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step: jobName }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast.success("Job Started", {
          description: `${stepConfig.name} job queued successfully (ID: ${data.job_id?.slice(0, 8)}...)`,
        });
      } else {
        throw new Error(data.error || "Failed to start job");
      }
    } catch (error) {
      toast.error("Error", {
        description: error instanceof Error ? error.message : "Failed to start job",
      });
    } finally {
      setIsRunning(false);
    }
  };

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
            <Button className="gap-2" onClick={handleRunNow} disabled={isRunning}>
              <MaterialIcon name={isRunning ? "sync" : "play_arrow"} className={`text-lg ${isRunning ? "animate-spin" : ""}`} />
              {isRunning ? "Running..." : "Run Now"}
            </Button>
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

      {/* Tabs Section */}
      <Tabs defaultValue="logs" className="space-y-4">
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
