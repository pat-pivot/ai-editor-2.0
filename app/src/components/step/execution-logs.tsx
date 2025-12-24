"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export function ExecutionLogs({ stepId, stepName }: ExecutionLogsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Execution History */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Execution History</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MaterialIcon name="history" className="text-4xl text-gray-400 mb-3" />
            <p className="text-gray-600 font-medium">No executions recorded yet</p>
            <p className="text-gray-500 text-sm mt-1">
              Execution history will appear here when jobs run.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Log Detail */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Execution Detail</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="flex flex-col items-center justify-center py-12 text-center rounded-md border bg-gray-50">
            <MaterialIcon name="terminal" className="text-4xl text-gray-400 mb-3" />
            <p className="text-gray-600 font-medium">No logs available</p>
            <p className="text-gray-500 text-sm mt-1">
              Select an execution to view detailed logs.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
