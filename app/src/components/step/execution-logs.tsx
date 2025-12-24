"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

function MaterialIcon({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn("material-symbols-outlined", className)}>
      {name}
    </span>
  );
}

interface ExecutionLogsProps {
  stepId: number;
  stepName: string;
}

interface ExecutionEntry {
  id: string;
  timestamp: string;
  status: "success" | "warning" | "error";
  duration: string;
  storiesIn?: number;
  storiesOut?: number;
}

interface LogLine {
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR";
  code: string;
  message: string;
}

// Mock data - in production this would come from an API
const mockExecutions: ExecutionEntry[] = [
  { id: "1", timestamp: "Dec 23, 9:00 PM", status: "success", duration: "1m 42s", storiesIn: 156, storiesOut: 47 },
  { id: "2", timestamp: "Dec 22, 9:00 PM", status: "success", duration: "1m 38s", storiesIn: 148, storiesOut: 52 },
  { id: "3", timestamp: "Dec 21, 9:00 PM", status: "success", duration: "1m 45s", storiesIn: 161, storiesOut: 49 },
  { id: "4", timestamp: "Dec 20, 9:00 PM", status: "warning", duration: "2m 12s", storiesIn: 134, storiesOut: 38 },
  { id: "5", timestamp: "Dec 19, 9:00 PM", status: "success", duration: "1m 41s", storiesIn: 152, storiesOut: 51 },
  { id: "6", timestamp: "Dec 18, 9:00 PM", status: "error", duration: "0m 45s", storiesIn: 145 },
  { id: "7", timestamp: "Dec 17, 9:00 PM", status: "success", duration: "1m 39s", storiesIn: 158, storiesOut: 48 },
];

const mockLogLines: LogLine[] = [
  { timestamp: "9:00:00.000", level: "INFO", code: "PREFILTER_START", message: "Initiating pre-filter job" },
  { timestamp: "9:00:00.234", level: "INFO", code: "AIRTABLE_READ", message: "Fetching Newsletter Stories" },
  { timestamp: "9:00:02.456", level: "INFO", code: "AIRTABLE_READ", message: "Retrieved 156 stories" },
  { timestamp: "9:00:02.789", level: "INFO", code: "AIRTABLE_READ", message: "Fetching Source Scores" },
  { timestamp: "9:00:03.123", level: "INFO", code: "AIRTABLE_READ", message: "Retrieved 19 sources" },
  { timestamp: "9:00:03.456", level: "INFO", code: "GEMINI_CALL", message: "Processing batch 1/16" },
  { timestamp: "9:00:08.789", level: "INFO", code: "GEMINI_RESPONSE", message: "Batch 1 complete: 10 candidates" },
  { timestamp: "9:00:09.012", level: "INFO", code: "GEMINI_CALL", message: "Processing batch 2/16" },
  { timestamp: "9:00:14.345", level: "INFO", code: "GEMINI_RESPONSE", message: "Batch 2 complete: 8 candidates" },
  { timestamp: "9:00:14.567", level: "DEBUG", code: "BATCH_PROGRESS", message: "12.5% complete (2/16 batches)" },
  { timestamp: "9:01:35.123", level: "INFO", code: "GEMINI_RESPONSE", message: "Batch 16 complete: 5 candidates" },
  { timestamp: "9:01:35.456", level: "INFO", code: "FILTER_SUMMARY", message: "47 candidates passed filters" },
  { timestamp: "9:01:38.234", level: "INFO", code: "AIRTABLE_WRITE", message: "Writing to Pre-Filter Log" },
  { timestamp: "9:01:41.567", level: "INFO", code: "AIRTABLE_WRITE", message: "Wrote 47 candidate records" },
  { timestamp: "9:01:42.000", level: "INFO", code: "PREFILTER_COMPLETE", message: "Success" },
];

export function ExecutionLogs({ stepId, stepName }: ExecutionLogsProps) {
  const [selectedExecution, setSelectedExecution] = useState<string | null>("1");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Execution History */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Execution History</CardTitle>
          <CardAction>
            <Button variant="outline" size="sm" className="gap-2">
              <MaterialIcon name="download" className="text-base" />
              Export CSV
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="pt-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead className="text-right">In</TableHead>
                <TableHead className="text-right">Out</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockExecutions.map((execution) => (
                <TableRow
                  key={execution.id}
                  className={cn(
                    "cursor-pointer",
                    selectedExecution === execution.id && "bg-muted/50"
                  )}
                  onClick={() => setSelectedExecution(execution.id)}
                >
                  <TableCell className="font-medium">{execution.timestamp}</TableCell>
                  <TableCell>
                    <StatusBadge status={execution.status} />
                  </TableCell>
                  <TableCell className="font-mono text-muted-foreground">
                    {execution.duration}
                  </TableCell>
                  <TableCell className="text-right">{execution.storiesIn}</TableCell>
                  <TableCell className="text-right">
                    {execution.storiesOut ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Log Detail */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">
            Execution Detail
            {selectedExecution && (
              <span className="font-normal text-muted-foreground ml-2">
                {mockExecutions.find((e) => e.id === selectedExecution)?.timestamp}
              </span>
            )}
          </CardTitle>
          <CardAction>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <MaterialIcon name="content_copy" className="text-base" />
                Copy
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <MaterialIcon name="download" className="text-base" />
                Download
              </Button>
            </div>
          </CardAction>
        </CardHeader>
        <CardContent className="pt-0">
          <ScrollArea className="h-[400px] rounded-md border bg-muted/30">
            <div className="p-4 font-mono text-xs space-y-1">
              {mockLogLines.map((line, index) => (
                <LogLineEntry key={index} line={line} />
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

function StatusBadge({ status }: { status: "success" | "warning" | "error" }) {
  const config = {
    success: { icon: "check_circle", label: "OK", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    warning: { icon: "warning", label: "WARN", className: "bg-amber-100 text-amber-700 border-amber-200" },
    error: { icon: "error", label: "ERROR", className: "bg-red-100 text-red-700 border-red-200" },
  }[status];

  return (
    <Badge variant="outline" className={cn("gap-1", config.className)}>
      <MaterialIcon name={config.icon} className="text-xs" />
      {config.label}
    </Badge>
  );
}

function LogLineEntry({ line }: { line: LogLine }) {
  const levelColors = {
    DEBUG: "text-muted-foreground",
    INFO: "text-blue-600",
    WARN: "text-amber-600",
    ERROR: "text-red-600",
  };

  return (
    <div className="flex gap-2 hover:bg-muted/50 px-2 py-0.5 rounded">
      <span className="text-muted-foreground shrink-0">{line.timestamp}</span>
      <span className={cn("w-12 shrink-0 font-semibold", levelColors[line.level])}>
        {line.level}
      </span>
      <span className="text-primary shrink-0">[{line.code}]</span>
      <span className="text-foreground">{line.message}</span>
    </div>
  );
}
