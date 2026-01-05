"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";

interface ExecutionLogsProps {
  stepId: number;
  stepName: string;
}

// Execution logs will be loaded from the worker logs API in a future update
// For now, show an empty state

export function ExecutionLogs({ stepId, stepName }: ExecutionLogsProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base">
          Execution Logs
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="h-[300px] rounded-md border bg-muted/30 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <FileText className="h-10 w-10 mx-auto mb-2" />
            <p className="text-sm">Execution logs will be available in a future update.</p>
            <p className="text-xs mt-1">View worker logs in the Render dashboard for now.</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
